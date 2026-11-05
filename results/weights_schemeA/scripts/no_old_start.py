"""A4 follow-up (audit finding 1): the old weights (rev10 F_hw_m4_firstpass, fitted on all 210 training samples, so they
have seen S and every CV validation fold) were one of the optimiser starts in families a-c. This re-runs the CV of the
three chosen configurations without that start (and, for b/c, with the a_m20 start also trained without it), all 20
splits, same seeds and settings otherwise, and compares the CV score S. Training data only; no SPICE.
-> summary/A4_jobs_noold/*.json, summary/A4_no_old_start.json"""
import json, sys, time
import numpy as np
from multiprocessing import Pool
import wcommon as W
import surrogate as SG
import train as TR
from cv_eval import metrics, aggregate

OUT = W.SUMM / "A4_jobs_noold"
CHOSEN = [("a", "le60", 30), ("b", "le60", "20"), ("c", "le60", "10")]


def job(args):
    fam, mode, cfg, k = args
    f = OUT / f"{fam}_{mode}_{TR.cfg_tag(cfg)}_{k:02d}.json"
    if f.exists():
        return json.loads(f.read_text())
    tr = np.array(TR.SPL["cv_T"][k]["train"]); X, y = W.XTR[tr], W.YTR[tr]
    t0 = time.time()
    if fam == "a":
        F, info = TR.train_a(X, y, cfg, mode, include_old=False)
    else:
        Fa = np.array(job(("a", mode, TR.A_START_M, k))["F"])
        starts = [("lr0.001", TR.lr_start(X, y, 1e-3)), (f"a_m{TR.A_START_M}", Fa)]
        tau, m = TR.parse_bc(cfg)
        F, info = TR.train_bc(X, y, fam, cfg, starts, seed=100 * (k + 1) + int(tau * 10) + int(m * 1000), mode=mode)
    r = dict(family=fam, mode=mode, config=cfg, split=k, F=np.asarray(F).tolist(), info=info, wall_s=round(time.time() - t0, 1))
    f.write_text(json.dumps(r, indent=1, default=float))
    return r


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    nproc = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    ks = range(len(TR.SPL["cv_T"]))
    with Pool(nproc) as p:                      # a first (b/c use the a_m20 no-old start of the same split)
        list(p.imap_unordered(job, [("a", "le60", 30, k) for k in ks] + [("a", "le60", TR.A_START_M, k) for k in ks]))
        list(p.imap_unordered(job, [(f, md, c, k) for f, md, c in CHOSEN[1:] for k in ks]))
    dies = SG.make_dies(250, (20, 35), 41000)
    qs = {f"{v:.2f}": SG.corner_params(v) for v in TR.VTH_GRID}
    cv = json.loads((W.SUMM / "A1_cv.json").read_text())["families"]
    res = {}
    for fam, mode, cfg in CHOSEN:
        rows = []
        n_changed = 0
        for k in ks:
            j_new = json.loads((OUT / f"{fam}_{mode}_{TR.cfg_tag(cfg)}_{k:02d}.json").read_text())
            j_old = json.loads((TR.JOBS / f"{fam}_{mode}_{TR.cfg_tag(cfg)}_{k:02d}.json").read_text())
            n_changed += j_new["F"] != j_old["F"]
            m = metrics(np.array(j_new["F"]), np.array(TR.SPL["cv_T"][k]["val"]), dies, qs); m.update(split=k); rows.append(m)
        key = f"{mode}_{TR.cfg_tag(cfg)}"
        res[f"{fam}_{key}"] = dict(reported=cv[fam][key], without_old_start=aggregate(rows), splits_with_different_weights=n_changed)
    (W.SUMM / "A4_no_old_start.json").write_text(json.dumps(res, indent=1))
    for k, v in res.items():
        print(k, "S reported", v["reported"]["S"], "-> without old start", v["without_old_start"]["S"], "| splits changed", v["splits_with_different_weights"])
