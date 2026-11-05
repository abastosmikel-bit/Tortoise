"""Race-surrogate objectives for integer weight search (A1). Mean over corners x dies x samples of phi(M - m), where
M = min_{j != y}(t_j - t_y) - G_res (surrogate.py), m = extra margin [us], phi = step (tau = 0) or sigmoid(./tau);
a trip during C1 scores 0. A move changes one column, so only that class's trip times are recomputed."""
import numpy as np
from numba import njit
import surrogate as SG


@njit(cache=False)
def _val_numba(t, c1, k, tk, ck, y, G, m, tau, tie):
    """Objective with column k replaced by (tk, ck), without copying t. t: (C,D,N,5), tk: (C,D,N)."""
    C, D, N, _ = t.shape
    tot = 0.0; tot2 = 0.0
    for c in range(C):
        for d in range(D):
            for n in range(N):
                yy = y[n]
                ty = tk[c, d, n] if yy == k else t[c, d, n, yy]
                mn = np.inf; bad = False
                for j in range(5):
                    if j == k:
                        tj = tk[c, d, n]; cj = ck[c, d, n]
                    else:
                        tj = t[c, d, n, j]; cj = c1[c, d, n, j]
                    if cj:
                        bad = True
                    if j != yy and tj < mn:
                        mn = tj
                if bad:
                    continue
                M = mn - ty - G[c] - m
                if tau > 0:
                    z = M / tau
                    z = min(max(z, -60.0), 60.0)
                    tot += 1.0 / (1.0 + np.exp(-z))
                elif M >= 0:
                    tot += 1.0
                if tie > 0:
                    z = min(max(M / 5.0, -60.0), 60.0)
                    tot2 += 1.0 / (1.0 + np.exp(-z))
    return (tot + tie * tot2) / (C * D * N)

FMAX = 60


class RaceObjective:
    def __init__(self, X, y, corners, dies=None, tau=0.0, m=0.0, tie=0.0):
        self.X = np.asarray(X, float); self.y = np.asarray(y); self.N = len(y)
        self.qs = list(corners); self.tau, self.m, self.tie = tau, m, tie
        self.D = 1 if dies is None else dies.n
        if dies is None:
            self.dR = np.zeros((1, 5)); self.dT = np.zeros((1, 5))
            self.G1 = self.G2 = None
        else:
            self.dR, self.dT = dies.offsets()
            f = np.arange(FMAX + 1)
            sig = dies.anchor[:, None] * np.sqrt(780.0 / (540.0 * np.maximum(f, 1)))[None]          # (D, 61)
            d = dies.z_bank[:, :, :, None] * sig[:, None, None, :]                                 # (D,6,5,61)
            self.G1, self.G2 = SG.g_of(d, 1), SG.g_of(d, 2)
        self.rows = np.arange(6)
        self.iy = np.arange(self.N)

    def column(self, F, k):
        """t (C, D, N) and C1-trip flag for class k."""
        fk = np.asarray(F[:, k], int)
        if self.G1 is None:
            g1 = np.ones((1, 6)); g2 = g1
        else:
            g1 = self.G1[:, self.rows, k, fk]; g2 = self.G2[:, self.rows, k, fk]                   # (D,6)
        Fe1 = fk[None] * g1; Fe2 = fk[None] * g2
        A = Fe1 @ self.X.T                                                                         # (D,N)
        S1 = Fe1.sum(1)[:, None]; S2 = Fe2.sum(1)[:, None]
        ts, cs = [], []
        for q in self.qs:
            V = q["R"][k] + self.dR[:, k:k + 1] + q["alpha"] * (q["T1"] * A + q["WMIN"] * S1) + q["c0"]
            thr = q["Theta"][k] + self.dT[:, k:k + 1]
            ts.append(q.get("gap_factor", 1.0) * (thr - V) / (q["gamma"] * S2)); cs.append(V >= thr)   # gap-scaled times
        return np.stack(ts), np.stack(cs)

    def _value(self, t, c1):
        ty = t[:, :, self.iy, self.y]                                                              # (C,D,N)
        tt = t.copy(); tt[:, :, self.iy, self.y] = np.inf
        G = np.array([q["G_res"] for q in self.qs])[:, None, None]
        M = tt.min(3) - ty - G - self.m
        bad = c1.any(3)
        if self.tau > 0:
            v = 1 / (1 + np.exp(-np.clip(M / self.tau, -60, 60)))
        else:
            v = (M >= 0).astype(float)
        v = np.where(bad, 0.0, v)
        val = v.mean()
        if self.tie:
            val += self.tie * np.where(bad, 0.0, 1 / (1 + np.exp(-np.clip(M / 5.0, -60, 60)))).mean()
        return val

    def init(self, F):
        cols = [self.column(F, k) for k in range(5)]
        self.t = np.ascontiguousarray(np.stack([c[0] for c in cols], 3)); self.c1 = np.ascontiguousarray(np.stack([c[1] for c in cols], 3))
        self.F = np.array(F, int)
        self.val = self._value(self.t, self.c1)
        return self.val

    def try_col(self, Fnew, k):
        tk, ck = self.column(Fnew, k)
        G = np.array([q["G_res"] for q in self.qs], float)
        v = _val_numba(self.t, self.c1, k, np.ascontiguousarray(tk), np.ascontiguousarray(ck), self.y.astype(np.int64), G,
                       float(self.m), float(self.tau), float(self.tie))
        return v, (k, tk, ck, np.array(Fnew, int))

    def commit(self, cache, val):
        k, tk, ck, F = cache
        self.t[..., k] = tk; self.c1[..., k] = ck; self.F = F; self.val = val

    def __call__(self, F):
        return self.init(F)


def anneal(objective, F0, n_iter=20000, T0=3e-3, T1=3e-5, seed=0, max_step=3, nnz=(15, 21), colsum=(60, 60)):
    """Simulated annealing over feasible integer moves: shift d fingers from row a to row b of one column; if the
    column-sum range allows (colsum[0] < 60), also remove or add d fingers in one bank."""
    rng = np.random.default_rng(seed)
    F = np.array(F0, int); cur = objective.init(F)
    best, bestF = cur, F.copy()
    free = colsum[0] < colsum[1]
    for it in range(n_iter):
        T = T0 * (T1 / T0) ** (it / max(n_iter - 1, 1))
        k = rng.integers(5)
        kind = 0 if not free else rng.choice(3, p=(0.6, 0.2, 0.2))
        d = int(rng.integers(1, max_step + 1))
        G = F.copy()
        if kind in (0, 1):
            src = np.flatnonzero(F[:, k] > 0)
            a = src[rng.integers(len(src))]; d = min(d, int(F[a, k])); G[a, k] -= d
        if kind in (0, 2):
            b = rng.integers(5)
            if kind == 0:
                b = b + (b >= a)
            else:
                b = rng.integers(6)
            G[b, k] += d
        if not (nnz[0] <= (G > 0).sum() <= nnz[1] and colsum[0] <= G[:, k].sum() <= colsum[1]):
            continue
        v, cache = objective.try_col(G, k)
        if v >= cur or rng.random() < np.exp((v - cur) / T):
            objective.commit(cache, v); F, cur = G, v
            if cur > best + 1e-15:
                best, bestF = cur, F.copy()
    return bestF, best


def neighbours(F, max_step=3, nnz=(15, 21), colsum=(60, 60)):
    nz0 = (F > 0).sum()
    for k in range(5):
        n = F[:, k].sum()
        for a in range(6):
            for d in range(1, max_step + 1):
                if F[a, k] >= d:
                    for b in range(6):
                        if b == a:
                            continue
                        nz = nz0 - (F[a, k] == d) + (F[b, k] == 0)
                        if nnz[0] <= nz <= nnz[1]:
                            G = F.copy(); G[a, k] -= d; G[b, k] += d
                            yield k, G
                    if colsum[0] <= n - d and nnz[0] <= nz0 - (F[a, k] == d):
                        G = F.copy(); G[a, k] -= d
                        yield k, G
                if n + d <= colsum[1] and nz0 + (F[a, k] == 0) <= nnz[1]:
                    G = F.copy(); G[a, k] += d
                    yield k, G


def descend(objective, F0, max_step=3, nnz=(15, 21), max_iter=2000, colsum=(60, 60)):
    """Greedy best-improvement descent over all feasible moves (incremental)."""
    F = np.array(F0, int); cur = objective.init(F)
    for _ in range(max_iter):
        best = None
        for k, G in neighbours(F, max_step, nnz, colsum):
            v, cache = objective.try_col(G, k)
            if v > cur + 1e-12 and (best is None or v > best[0]):
                best = (v, cache, G)
        if best is None:
            break
        objective.commit(best[1], best[0]); cur, F = best[0], best[2]
    return F, cur
