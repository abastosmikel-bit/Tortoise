"""Optimisers shared by the ceilings (A0) and the candidates (A1). Training data only.
 * fit_lr     : multinomial logistic regression with optional bias and optional equal-column-sum constraint (L-BFGS).
 * to_fingers : constrained float weights -> integer fingers (non-negative, column sums 60, 15..21 non-empty banks).
 * milp_count : exact MILP (HiGHS): maximise the number of samples whose score margin over every other class meets a
                per-sample/per-class requirement, with the hardware constraints of DECISIONS.md W1.
 * local_search: integer moves (shift fingers between rows of a column) maximising any objective f(F)."""
import numpy as np
import highspy
from scipy.optimize import minimize
from scipy.sparse import coo_matrix

COLSUM, NNZ_MIN, NNZ_MAX = 60, 15, 21


# ----------------------------------------------------------------------------- logistic regression
def _canon(V, bias, eqcol):
    """Map free parameters to the classifier family. eqcol: weights double-centred (zero row and column sums), which is
    the canonical form of 'equal column sums, no per-row offset' (row shifts don't change the argmax)."""
    W = V[:6]
    if eqcol:
        W = W - W.mean(1, keepdims=True) - W.mean(0, keepdims=True) + W.mean()
    else:
        W = W - W.mean(1, keepdims=True)          # row shifts are invisible to softmax; remove them
    b = V[6] - V[6].mean() if bias else np.zeros(5)
    return W, b


def fit_lr(X, y, lam, bias=True, eqcol=False):
    n = len(y); Y = np.eye(5)[y]

    def f(v):
        V = v.reshape(7, 5)
        W, b = _canon(V, bias, eqcol)
        Z = X @ W + b
        Z = Z - Z.max(1, keepdims=True)
        P = np.exp(Z); P /= P.sum(1, keepdims=True)
        loss = -np.sum(Y * np.log(P + 1e-300)) / n + lam * (np.sum(W * W) + np.sum(b * b))
        G = (P - Y) / n
        gW = X.T @ G + 2 * lam * W
        gb = G.sum(0) + 2 * lam * b
        # chain rule through the (linear, symmetric) centring projections
        if eqcol:
            gW = gW - gW.mean(1, keepdims=True) - gW.mean(0, keepdims=True) + gW.mean()
        else:
            gW = gW - gW.mean(1, keepdims=True)
        gb = gb - gb.mean() if bias else np.zeros(5)
        return loss, np.vstack([gW, gb]).ravel()
    r = minimize(f, np.zeros(35), jac=True, method="L-BFGS-B", options=dict(maxiter=5000, gtol=1e-9))
    W, b = _canon(r.x.reshape(7, 5), bias, eqcol)
    return W, b


def predict(X, W, b=None):
    s = X @ W + (0 if b is None else b)
    return np.argmax(s, 1)


# ----------------------------------------------------------------------------- integer fingers
def to_fingers(W):
    """Double-centred float weights -> integer fingers. Shift each row by its minimum (row shifts are invisible), which
    makes every column sum equal; scale to 60; round per column by largest remainder; then enforce 15..21 banks by
    zeroing the smallest banks (their fingers go to the largest bank of the same column)."""
    W = np.asarray(W, float)
    W = W - W.mean(1, keepdims=True) - W.mean(0, keepdims=True) + W.mean()
    P = W - W.min(1, keepdims=True)
    P = P * COLSUM / P.sum(0, keepdims=True)
    F = np.floor(P).astype(int)
    for k in range(5):
        r = COLSUM - F[:, k].sum()
        order = np.argsort(-(P[:, k] - F[:, k]), kind="stable")
        F[order[:r], k] += 1
    while (F > 0).sum() > NNZ_MAX:
        i, k = np.unravel_index(np.argmin(np.where(F > 0, F, 10 ** 6)), F.shape)
        v = F[i, k]; F[i, k] = 0; F[np.argmax(F[:, k]), k] += v
    while (F > 0).sum() < NNZ_MIN:            # open the empty bank with the largest float weight (1 finger)
        cand = [(P[i, k], i, k) for i in range(6) for k in range(5) if F[i, k] == 0 and F[:, k].max() > 1]
        _, i, k = max(cand)
        F[np.argmax(F[:, k]), k] -= 1; F[i, k] += 1
    assert (F.sum(0) == COLSUM).all() and NNZ_MIN <= (F > 0).sum() <= NNZ_MAX
    return F


def feasible(F, colsum=(COLSUM, COLSUM)):
    F = np.asarray(F)
    return bool((F >= 0).all() and (F.sum(0) >= colsum[0]).all() and (F.sum(0) <= colsum[1]).all()
                and NNZ_MIN <= (F > 0).sum() <= NNZ_MAX)


def moves(F, max_step=1):
    """All feasible single moves: shift d (1..max_step) fingers from row a to row b within a column."""
    nnz = (F > 0).sum()
    for k in range(5):
        for a in range(6):
            if F[a, k] == 0:
                continue
            for b in range(6):
                if a == b:
                    continue
                for d in range(1, min(max_step, F[a, k]) + 1):
                    dn = nnz - (1 if F[a, k] == d else 0) + (1 if F[b, k] == 0 else 0)
                    if NNZ_MIN <= dn <= NNZ_MAX:
                        yield k, a, b, d


def local_search(F, f, max_step=1, max_iter=10000):
    """Greedy best-improvement descent on f (to maximise) over integer moves."""
    F = np.array(F, int); best = f(F)
    for _ in range(max_iter):
        cand = None
        for k, a, b, d in moves(F, max_step):
            G = F.copy(); G[a, k] -= d; G[b, k] += d
            v = f(G)
            if v > best + 1e-12 and (cand is None or v > cand[0]):
                cand = (v, G)
        if cand is None:
            break
        best, F = cand
    return F, best


# ----------------------------------------------------------------------------- MILP
def milp_count(X, y, req, time_limit=600.0, start=None, threads=1, weights=None, max_nodes=None):
    """maximise sum_n w_n z_n  s.t.  x_n.(F[:,y_n] - F[:,j]) >= req[n, j] - M_nj (1 - z_n)  for all j != y_n,
    F integer >= 0, column sums 60, b_ik binary with b <= F <= 60 b, 15 <= sum b <= 21.
    req: (N, 5) required score margin in finger units (column y_n ignored). Returns (F, info)."""
    N = len(y); w = np.ones(N) if weights is None else np.asarray(weights, float)
    nF, nB = 30, 30
    iF = lambda i, k: i * 5 + k
    iB = lambda i, k: nF + i * 5 + k
    iZ = lambda n: nF + nB + n
    ncol = nF + nB + N
    rows, cols, vals, lo, hi = [], [], [], [], []
    r = 0

    def add(entries, l, u):
        nonlocal r
        for c, v in entries:
            rows.append(r); cols.append(c); vals.append(v)
        lo.append(l); hi.append(u); r += 1
    for k in range(5):
        add([(iF(i, k), 1.0) for i in range(6)], COLSUM, COLSUM)
    for i in range(6):
        for k in range(5):
            add([(iF(i, k), 1.0), (iB(i, k), -COLSUM)], -highspy.kHighsInf, 0.0)
            add([(iF(i, k), 1.0), (iB(i, k), -1.0)], 0.0, highspy.kHighsInf)
    add([(iB(i, k), 1.0) for i in range(6) for k in range(5)], NNZ_MIN, NNZ_MAX)
    for n in range(N):
        x = X[n]; yy = y[n]
        for j in range(5):
            if j == yy:
                continue
            M = req[n, j] + COLSUM * (x.max() - x.min()) + 1e-6     # x.F_y >= 60 min x, x.F_j <= 60 max x
            e = [(iF(i, yy), x[i]) for i in range(6) if x[i] != 0] + [(iF(i, j), -x[i]) for i in range(6) if x[i] != 0]
            add(e + [(iZ(n), -M)], req[n, j] - M, highspy.kHighsInf)
    A = coo_matrix((vals, (rows, cols)), shape=(r, ncol)).tocsc()
    lp = highspy.HighsLp()
    lp.num_col_, lp.num_row_ = ncol, r
    lp.col_cost_ = np.concatenate([np.zeros(nF + nB), w])
    lp.col_lower_ = np.zeros(ncol)
    lp.col_upper_ = np.concatenate([np.full(nF, COLSUM), np.ones(nB + N)])
    lp.row_lower_, lp.row_upper_ = np.array(lo), np.array(hi)
    lp.sense_ = highspy.ObjSense.kMaximize
    lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
    lp.a_matrix_.start_, lp.a_matrix_.index_, lp.a_matrix_.value_ = A.indptr, A.indices, A.data
    lp.integrality_ = [highspy.HighsVarType.kInteger] * ncol
    h = highspy.Highs()
    opts = dict(output_flag=False, time_limit=float(time_limit), threads=threads, random_seed=0, mip_rel_gap=0.0)
    if max_nodes is not None:        # deterministic budget (the time limit is then only a safety net)
        opts["mip_max_nodes"] = int(max_nodes)
    for k_, v_ in opts.items():
        h.setOptionValue(k_, v_)
    h.passModel(lp)
    if start is not None:
        S = np.asarray(start, int)
        sol = np.zeros(ncol)
        for i in range(6):
            for k in range(5):
                sol[iF(i, k)] = S[i, k]; sol[iB(i, k)] = 1.0 if S[i, k] > 0 else 0.0
        s = X @ S
        for n in range(N):
            ok = all(s[n, y[n]] - s[n, j] >= req[n, j] for j in range(5) if j != y[n])
            sol[iZ(n)] = 1.0 if ok else 0.0
        hs = highspy.HighsSolution(); hs.col_value = list(sol); h.setSolution(hs)
    h.run()
    info = h.getInfo()
    st = h.modelStatusToString(h.getModelStatus())
    v = np.array(h.getSolution().col_value)
    F = np.rint(v[:nF]).astype(int).reshape(6, 5)
    out = dict(status=st, objective=float(info.objective_function_value), bound=float(info.mip_dual_bound),
               gap=float(info.mip_gap), nodes=int(info.mip_node_count), time_limit=time_limit, max_nodes=max_nodes)
    assert feasible(F), F
    return F, out


def count_margin(F, X, y, req):
    s = X @ F
    d = s[np.arange(len(y)), y][:, None] - s
    ok = d >= req
    ok[np.arange(len(y)), y] = True
    return ok.all(1)
