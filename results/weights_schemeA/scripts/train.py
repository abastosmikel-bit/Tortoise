"""A1 candidate training (DECISIONS.md W7), training pool T only (170 samples; S is never read here).
Usage: python3 train.py <a|b|c> [nproc]                  CV: every (mode, config) x the 20 group splits of T -> summary/A1_jobs/*.json
       python3 train.py final <a|b|c> <mode> <config>     retrain the chosen config on all of T  -> weights/cand_<fam>.npy
Column-sum mode (W13): eq60 (all column sums 60) or le60 (50..60).
Families:
 a  margin-maximising, nominal surrogate at 0.65 V: maximise #{samples: correct class wins by gap >= G_res + m}.
    Starts: rounded constrained-float LR (lambda 1e-4/1e-3/1e-2) and the old weights -> greedy descent on the exact
    count (tie-break 1e-3 x mean sigmoid) -> exact MILP polish (HiGHS, 3000 nodes, warm-started). Config = m [us].
 b  mismatch-aware: mean over 128 training dies (64 at 20 mV, 64 at 35 mV; seed 31000) of phi(M), tau in {0, 2, 5} us.
    Starts: rounded LR (1e-3), family a at m = 20 us on the same split, old weights -> annealing (20000 moves) -> greedy
    descent; best of the 3 on the training objective. Config = tau.
 c  re-trim-aware: as b, averaged over re-trimmed |V_th| 0.55/0.65/0.75/0.85/0.95 V. Config = tau."""
import json, sys, time
import numpy as np
from multiprocessing import Pool
import wcommon as W
import optim as O
import surrogate as SG
from obj import RaceObjective, anneal, descend

SPL = json.loads((W.SUMM / "splits.json").read_text())
T = np.array(SPL["T"])
JOBS = W.SUMM / "A1_jobs"
CONFIGS = {"a": [0, 5, 10, 20, 30, 45, 60], "b": [0, 2, 5, "10", "20", "5m15", "5m30"], "c": [0, 2, 5, "10", "20", "5m15", "5m30"]}
# b/c configs are tau [us] or "<tau>m<m>" (W14: objective sigma((M - m)/tau)); a configs are the margin m [us]
MODES = {"eq60": (60, 60), "le60": (50, 60)}          # W13
VTH_GRID = (0.55, 0.65, 0.75, 0.85, 0.95)
A_START_M = 20


def lr_start(X, y, lam):
    Wt, _ = O.fit_lr(X, y, lam, False, True)
    return O.to_fingers(Wt)


def train_a(X, y, m, mode="eq60", include_old=True):
    cs = MODES[mode]
    q = SG.corner_params(0.65)
    obj = RaceObjective(X, y, [q], None, tau=0.0, m=m, tie=1e-3)
    tried = []
    best = None
    for name, F0 in [(f"lr{lam:g}", lr_start(X, y, lam)) for lam in (1e-4, 1e-3, 1e-2)] + ([("old", W.F_OLD)] if include_old else []):
        F, v = descend(obj, F0, colsum=cs)
        tried.append(dict(start=name, value=float(v)))
        if best is None or v > best[0] + 1e-12:
            best = (v, F, name)
    if mode != "eq60":                                     # no MILP for unequal column sums (W13)
        return best[1], dict(tried=tried, chosen="local_search", train_count=int(round(float(SG.accuracy(best[1], X, y, q, None)[0]) * len(y))) if m == 0 else None,
                             train_objective=float(best[0]), n=len(y))
    req = SG.req_nominal(X, y, q, m)
    Fm, info = O.milp_count(X, y, req, time_limit=3600, start=best[1], max_nodes=3000)
    c_ls = int(O.count_margin(best[1], X, y, req).sum()); c_m = int(O.count_margin(Fm, X, y, req).sum())
    F = Fm if c_m >= c_ls else best[1]
    return F, dict(tried=tried, ls_count=c_ls, milp_count=c_m, milp=info, chosen="milp" if c_m >= c_ls else "local_search",
                   train_count=int(O.count_margin(F, X, y, req).sum()), n=len(y))


def parse_bc(cfg):
    c = str(cfg)
    tau, m = (c.split("m") + ["0"])[:2] if "m" in c else (c, "0")
    return float(tau), float(m)


def cfg_tag(cfg):
    return f"{cfg:g}" if not isinstance(cfg, str) else cfg


def train_bc(X, y, fam, cfg, starts, seed, mode="eq60", timing=None):
    cs = MODES[mode]
    tau, m = parse_bc(cfg)
    dies = SG.make_dies(64, (20, 35), 31000)
    qs = [SG.corner_params(0.65, timing)] if fam == "b" else [SG.corner_params(v, timing) for v in VTH_GRID]
    obj = RaceObjective(X, y, qs, dies, tau=tau, m=m)
    exact = RaceObjective(X, y, qs, dies, tau=0.0)
    tried, best = [], None
    for j, (name, F0) in enumerate(starts):
        F1, v1 = anneal(obj, F0, n_iter=20000, seed=seed + j, colsum=cs)
        F2, v2 = descend(obj, F1, colsum=cs)
        tried.append(dict(start=name, start_value=float(obj.init(F0)), anneal=float(v1), descend=float(v2), exact=float(exact.init(F2))))
        if best is None or v2 > best[0] + 1e-12:
            best = (v2, F2, name)
    return best[1], dict(tried=tried, chosen_start=best[2], train_objective=float(best[0]), train_exact=float(exact.init(best[1])))


def job(args):
    fam, mode, cfg, k = args
    out = JOBS / f"{fam}_{mode}_{cfg_tag(cfg)}_{k:02d}.json"
    if out.exists():
        return json.loads(out.read_text())
    sp = SPL["cv_T"][k] if k >= 0 else dict(train=SPL["T"], val=[])
    tr = np.array(sp["train"])
    X, y = W.XTR[tr], W.YTR[tr]
    t0 = time.time()
    if fam == "a":
        F, info = train_a(X, y, cfg, mode)
    else:
        a_file = JOBS / f"a_{mode}_{A_START_M:g}_{k:02d}.json"
        Fa = np.array(json.loads(a_file.read_text())["F"])
        starts = [("lr0.001", lr_start(X, y, 1e-3)), (f"a_m{A_START_M}", Fa), ("old", W.F_OLD)]
        tau, m = parse_bc(cfg)
        F, info = train_bc(X, y, fam, cfg, starts, seed=100 * (k + 1) + int(tau * 10) + int(m * 1000), mode=mode)
    r = dict(family=fam, mode=mode, config=cfg, split=k, F=np.asarray(F).tolist(), banks=int((np.asarray(F) > 0).sum()),
             n_tft=W.n_tft(F), info=info, wall_s=round(time.time() - t0, 1))
    out.write_text(json.dumps(r, indent=1, default=float))
    return r


if __name__ == "__main__":
    JOBS.mkdir(exist_ok=True)
    if sys.argv[1] == "final":
        fam, mode, cfg = sys.argv[2], sys.argv[3], sys.argv[4]
        cfg = float(cfg) if (fam == "a" or "m" not in cfg) and cfg not in ("10", "20") else cfg
        if fam != "a" and not (JOBS / f"a_{mode}_{A_START_M:g}_-1.json").exists():
            job(("a", mode, A_START_M, -1))
        r = job((fam, mode, cfg, -1))
        F = np.array(r["F"]); assert O.feasible(F, MODES[mode])
        np.save(W.WEIGHTS / f"cand_{fam}.npy", F)
        print(json.dumps({k: v for k, v in r.items() if k != "info"}, indent=1))
        sys.exit()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    fam = args[0]; nproc = int(args[1]) if len(args) > 1 else 4
    jobs = [(fam, md, c, k) for md in MODES for c in CONFIGS[fam] for k in range(len(SPL["cv_T"]))]
    if "--reverse" in sys.argv:          # a second worker pool can take the list from the other end (results are deterministic)
        jobs = jobs[::-1]
    t0 = time.time()
    with Pool(nproc) as p:
        for i, r in enumerate(p.imap_unordered(job, jobs), 1):
            print(f"[{i}/{len(jobs)} {time.time()-t0:6.0f}s] {fam} {r['mode']} cfg {r['config']} split {r['split']} banks {r['banks']} colsums {np.array(r['F']).sum(0).tolist()} wall {r['wall_s']}", flush=True)
