"""A0 software ceilings (DECISIONS.md W3): argmax of a linear score, no circuit, training data only.
Outer: the 50 group splits of all 210 training samples (summary/splits.json cv_all). Hyperparameters are chosen by an
inner group 4-fold CV on each outer training part (nested). A sample counts as correct only if its class's score is
strictly the largest.
Families:
  lr_bias_free     multinomial LR, per-class bias, free weights                     (general float linear)
  lr_nobias_free   no bias, free column sums
  lr_bias_eqcol    bias, equal column sums
  lr_nobias_eqcol  no bias, equal column sums = what the crossbar can realise in float (non-negativity is free:
                   row shifts are invisible to the race)
  svm_ovr / svm_cs LinearSVC one-vs-rest / Crammer-Singer, bias, free
  lda              shrinkage LDA
  int_round        lr_nobias_eqcol rounded to fingers (W1: column sums 60, 15..21 non-empty banks)
  int_ls           int_round + local search maximising the training count with score margin >= mu (mu by inner CV)
  int_milp         int_ls + MILP polish (HiGHS, same mu, 2000-node deterministic budget)
  old_weights      rev10 F_hw_m4_firstpass (trained on all 210: in-sample on every fold)
-> summary/A0_ceilings.json"""
import json, sys, time, warnings
import numpy as np
from multiprocessing import Pool
import wcommon as W
import optim as O

warnings.filterwarnings("ignore")
SPL = json.loads((W.SUMM / "splits.json").read_text())
X_ALL, Y_ALL, G_ALL = W.XTR, W.YTR, W.GTR
LAMS = (1e-5, 1e-4, 1e-3, 1e-2, 1e-1)
CS = (0.01, 0.1, 1.0, 10.0, 100.0)
MUS = (0.25, 1.0, 2.0)


def correct(scores, y):
    s = np.asarray(scores, float)
    sy = s[np.arange(len(y)), y]
    so = s.copy(); so[np.arange(len(y)), y] = -np.inf
    return sy > so.max(1)


def inner_splits(idx, seed):
    g = G_ALL[idx]
    ug = np.random.default_rng(seed).permutation(np.unique(g))
    return [(idx[~np.isin(g, p)], idx[np.isin(g, p)]) for p in np.array_split(ug, 4)]


def lr_scores(tr, te, lam, bias, eqcol):
    Wt, b = O.fit_lr(X_ALL[tr], Y_ALL[tr], lam, bias, eqcol)
    return X_ALL[te] @ Wt + b, (Wt, b)


def svm_scores(tr, te, C, mc):
    from sklearn.svm import LinearSVC
    m = LinearSVC(C=C, multi_class=mc, max_iter=200000, dual=True, random_state=0).fit(X_ALL[tr], Y_ALL[tr])
    return m.decision_function(X_ALL[te])


def pick(tr, seed, grid, fn):
    """Inner CV: the grid value with the best mean inner-validation accuracy (first one on ties)."""
    best = None
    for gv in grid:
        acc = np.mean([correct(fn(a, b, gv), Y_ALL[b]).mean() for a, b in inner_splits(tr, seed)])
        if best is None or acc > best[1] + 1e-12:
            best = (gv, acc)
    return best[0]


def int_objective(Xtr, ytr, mu):
    req = np.full((len(ytr), 5), mu)

    def f(F):
        s = Xtr @ F
        d = s[np.arange(len(ytr)), ytr][:, None] - s
        d[np.arange(len(ytr)), ytr] = np.inf
        m = d.min(1)
        return float((m >= mu).sum()) + 1e-3 * float((1 / (1 + np.exp(-(m - mu)))).sum())
    return f, req


def int_fit(tr, mu, lam, milp=False):
    Wt, _ = O.fit_lr(X_ALL[tr], Y_ALL[tr], lam, False, True)
    F0 = O.to_fingers(Wt)
    f, req = int_objective(X_ALL[tr], Y_ALL[tr], mu)
    F1, _ = O.local_search(F0, f, max_step=2)
    if not milp:
        return F0, F1, None
    F2, info = O.milp_count(X_ALL[tr], Y_ALL[tr], req, time_limit=3600, start=F1, max_nodes=2000)
    if O.count_margin(F2, X_ALL[tr], Y_ALL[tr], req).sum() < O.count_margin(F1, X_ALL[tr], Y_ALL[tr], req).sum():
        F2 = F1                                   # never worse than the start on the training objective
    return F0, F1, (F2, info)


def outer(k):
    sp = SPL["cv_all"][k]
    tr, te = np.array(sp["train"]), np.array(sp["val"])
    seed = 5000 + k
    ytr, yte = Y_ALL[tr], Y_ALL[te]
    res = {}
    for name, bias, eqcol in (("lr_bias_free", True, False), ("lr_nobias_free", False, False),
                              ("lr_bias_eqcol", True, True), ("lr_nobias_eqcol", False, True)):
        lam = pick(tr, seed, LAMS, lambda a, b, l: lr_scores(a, b, l, bias, eqcol)[0])
        s, (Wt, b) = lr_scores(tr, te, lam, bias, eqcol)
        res[name] = dict(val=int(correct(s, yte).sum()), n=len(te), hyper=lam,
                         train=int(correct(X_ALL[tr] @ Wt + b, ytr).sum()), ntr=len(tr))
        if name == "lr_nobias_eqcol":
            lam_eq = lam
    for name, mc in (("svm_ovr", "ovr"), ("svm_cs", "crammer_singer")):
        C = pick(tr, seed, CS, lambda a, b, c: svm_scores(a, b, c, mc))
        res[name] = dict(val=int(correct(svm_scores(tr, te, C, mc), yte).sum()), n=len(te), hyper=C)
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
    m = LDA(solver="lsqr", shrinkage="auto").fit(X_ALL[tr], ytr)
    res["lda"] = dict(val=int(correct(m.decision_function(X_ALL[te]), yte).sum()), n=len(te))
    # integer fingers
    mu = pick(tr, seed, MUS, lambda a, b, u: X_ALL[b] @ int_fit(a, u, lam_eq)[1])
    F0, F1, (F2, info) = int_fit(tr, mu, lam_eq, milp=True)
    for name, F in (("int_round", F0), ("int_ls", F1), ("int_milp", F2)):
        res[name] = dict(val=int(correct(X_ALL[te] @ F, yte).sum()), n=len(te), hyper=mu, lam=lam_eq,
                         train=int(correct(X_ALL[tr] @ F, ytr).sum()), ntr=len(tr), banks=int((F > 0).sum()), F=F.tolist())
    res["int_milp"]["milp"] = info
    res["old_weights"] = dict(val=int(correct(X_ALL[te] @ W.F_OLD, yte).sum()), n=len(te), note="in-sample")
    return k, res


if __name__ == "__main__":
    nproc = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    t0 = time.time(); per = {}
    with Pool(nproc) as p:
        for k, r in p.imap_unordered(outer, range(len(SPL["cv_all"]))):
            per[k] = r
            print(f"[{len(per)}/{len(SPL['cv_all'])} {time.time()-t0:6.0f}s] split {k}: " +
                  " ".join(f"{n}={v['val']}/{v['n']}" for n, v in r.items()), flush=True)
    names = list(per[0])
    summ = {}
    for n in names:
        reps = []
        for r in range(10):
            ks = [k for k in per if SPL["cv_all"][k]["repeat"] == r]
            reps.append(sum(per[k][n]["val"] for k in ks) / sum(per[k][n]["n"] for k in ks))
        tot_c = sum(per[k][n]["val"] for k in per); tot_n = sum(per[k][n]["n"] for k in per)
        summ[n] = dict(cv_accuracy_mean=round(float(np.mean(reps)), 4), cv_accuracy_sd_over_repeats=round(float(np.std(reps, ddof=1)), 4),
                       cv_accuracy_min_repeat=round(float(min(reps)), 4), cv_accuracy_max_repeat=round(float(max(reps)), 4),
                       pooled_correct=tot_c, pooled_n=tot_n)
        if "train" in per[0][n]:
            summ[n]["train_accuracy_mean"] = round(float(np.mean([per[k][n]["train"] / per[k][n]["ntr"] for k in per])), 4)
    # full-data fits (reported weights; not used for anything else)
    full = {}
    idx = np.arange(len(Y_ALL))
    lam = pick(idx, 99, LAMS, lambda a, b, l: lr_scores(a, b, l, False, True)[0])
    mu = pick(idx, 99, MUS, lambda a, b, u: X_ALL[b] @ int_fit(a, u, lam)[1])
    F0, F1, (F2, info) = int_fit(idx, mu, lam, milp=True)
    full = dict(lam=lam, mu=mu, int_round=F0.tolist(), int_ls=F1.tolist(), int_milp=F2.tolist(), milp=info,
                train_acc={n: round(float(correct(X_ALL @ F, Y_ALL).mean()), 4) for n, F in (("int_round", F0), ("int_ls", F1), ("int_milp", F2), ("old", W.F_OLD))})
    out = dict(protocol="DECISIONS.md W3; nested group CV, 10 repeats x 5 folds on the 210 training samples",
               summary=summ, full_data_integer_fits=full, per_split={str(k): per[k] for k in sorted(per)}, wall_s=round(time.time() - t0, 1))
    (W.SUMM / "A0_ceilings.json").write_text(json.dumps(out, indent=1, default=float))
    for n, v in summ.items():
        print(f"{n:16s} {v}")
