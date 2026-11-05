"""Fix the data partition of DECISIONS.md W2 (training data only; the test set is not touched).
 S  : 4 of the 21 training groups (40 samples), default_rng(20261025)       -> SPICE selection + held-out agreement
 T  : the other 17 groups (170 samples)                                      -> candidate training and CV
 K  : 40 samples of T, 8 per class, by the old weights' software margin      -> surrogate calibration
 cv_T   : 20 group splits of T (5 folds x 4 repeats, default_rng(1000 + r))
 cv_all : 50 group splits of all 210 (5 folds x 10 repeats, default_rng(2000 + r)) -> A0 ceilings only
Indices are into X_train. -> summary/splits.json"""
import json
import numpy as np
import wcommon as W


def group_folds(groups, n_folds, seed):
    g = np.random.default_rng(seed).permutation(np.unique(groups))
    parts = np.array_split(g, n_folds)
    return [sorted(int(x) for x in p) for p in parts]


def margins(F, X, y):
    s = X @ F
    sy = s[np.arange(len(y)), y]
    so = s.copy(); so[np.arange(len(y)), y] = -np.inf
    return sy - so.max(1)


if __name__ == "__main__":
    X, y, g = W.XTR, W.YTR, W.GTR
    groups = np.unique(g)
    S_groups = sorted(int(x) for x in np.random.default_rng(20261025).choice(groups, 4, replace=False))
    S = [int(i) for i in range(len(y)) if g[i] in S_groups]
    T = [int(i) for i in range(len(y)) if g[i] not in S_groups]
    m = margins(W.F_OLD, X, y)
    K = []
    for c in range(5):
        pool = [i for i in T if y[i] == c]
        near = sorted(pool, key=lambda i: (abs(m[i]), i))[:3]
        rest = sorted([i for i in pool if i not in near], key=lambda i: (m[i], i))
        qs = [rest[int(round(q * (len(rest) - 1)))] for q in (0.1, 0.3, 0.5, 0.7, 0.9)]
        assert len(set(qs)) == 5
        K += near + qs
    K = sorted(K)
    T_groups = sorted(int(x) for x in groups if x not in S_groups)
    gT = g[T]
    cv_T = []
    for r in range(4):
        folds = group_folds(gT, 5, 1000 + r)
        for f, fg in enumerate(folds):
            val = [i for i in T if g[i] in fg]
            cv_T.append(dict(repeat=r, fold=f, val_groups=fg, val=val, train=[i for i in T if g[i] not in fg]))
    cv_all = []
    for r in range(10):
        folds = group_folds(g, 5, 2000 + r)
        for f, fg in enumerate(folds):
            val = [i for i in range(len(y)) if g[i] in fg]
            cv_all.append(dict(repeat=r, fold=f, val_groups=fg, val=val, train=[i for i in range(len(y)) if g[i] not in fg]))
    out = dict(S_groups=S_groups, S=S, T_groups=T_groups, T=T, K=K,
               K_old_margin=[round(float(m[i]), 3) for i in K], K_labels=[int(y[i]) + 1 for i in K],
               S_class_counts=np.bincount(y[S], minlength=5).tolist(), K_class_counts=np.bincount(y[K], minlength=5).tolist(),
               cv_T=cv_T, cv_all=cv_all)
    (W.SUMM / "splits.json").write_text(json.dumps(out, indent=1))
    print("S groups", S_groups, "S class counts", out["S_class_counts"], "K class counts", out["K_class_counts"])
    print("K", K)
    print("K margins", out["K_old_margin"])
    print("cv_T fold sizes", [len(c["val"]) for c in cv_T[:5]], "cv_all fold sizes", [len(c["val"]) for c in cv_all[:5]])
