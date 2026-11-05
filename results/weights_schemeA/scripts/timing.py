"""Option (d) (DECISIONS.md W15): (c) plus co-optimised host timing. Training pool T only.
Usage: python3 timing.py screen [nproc]      the (c) family's CV-best (mode, config) trained at every timing of the grid
                                             on the 5 splits of CV repeat 0; S at that timing     -> summary/A1_d_screen.json
       python3 timing.py cv <T1> <WMIN> [nproc]   full 20-split CV at the chosen timing           -> summary/A1_d_cv.json
       python3 timing.py final <T1> <WMIN>        train on all of T at that timing                -> weights/cand_d.npy
       python3 timing.py spice <T1> <WMIN>        W15 (3)-(5): warm start at the timing, 20-run surrogate check on K, 40 S runs
       python3 timing.py check <T1> <WMIN>        evaluate the 20-run check                       -> summary/A1_d_check.json
Timing grid: T1 in {170, 200, 230, 260} us x WMIN in {20, 40} us; V2 offset fixed at 0.25 V and V1 offset at 0.83 V
(W15). The surrogate is evaluated at the timing (C1 drive and C1-trip checks change; per-finger parameters, trip levels and
G_res are the T1 = 170 us calibration, an assumption checked in SPICE for the chosen timing)."""
import json, sys, time
import numpy as np
from multiprocessing import Pool
import wcommon as W
import surrogate as SG
import train as TR
from cv_eval import metrics, aggregate

OUT = W.SUMM / "A1_jobs_d"
GRID = [(T1, WM) for T1 in (170, 200, 230, 260) for WM in (20, 40)]


def best_c():
    b = json.loads((W.SUMM / "A1_cv.json").read_text())["best_per_family"]["c"]
    return b["mode"], b["config"]


def job(args):
    T1, WM, k, mode, cfg = args
    f = OUT / f"d_T{T1}_W{WM}_{mode}_{cfg}_{k:02d}.json"
    if f.exists():
        return json.loads(f.read_text())
    timing = dict(T1=float(T1), WMIN=float(WM))
    sp = TR.SPL["cv_T"][k] if k >= 0 else dict(train=TR.SPL["T"])
    tr = np.array(sp["train"]); X, y = W.XTR[tr], W.YTR[tr]
    Fa = np.array(json.loads((TR.JOBS / f"a_{mode}_{TR.A_START_M:g}_{k:02d}.json").read_text())["F"])
    starts = [("lr0.001", TR.lr_start(X, y, 1e-3)), (f"a_m{TR.A_START_M}", Fa), ("old", W.F_OLD)]
    tau, m = TR.parse_bc(cfg)
    t0 = time.time()
    F, info = TR.train_bc(X, y, "c", cfg, starts, seed=100 * (k + 1) + int(tau * 10) + int(m * 1000), mode=mode, timing=timing)
    r = dict(T1=T1, WMIN=WM, mode=mode, config=cfg, split=k, F=np.asarray(F).tolist(), banks=int((F > 0).sum()), info=info,
             wall_s=round(time.time() - t0, 1))
    f.write_text(json.dumps(r, indent=1, default=float))
    return r


def evaluate(T1, WM, mode, cfg, splits):
    timing = dict(T1=float(T1), WMIN=float(WM))
    dies = SG.make_dies(250, (20, 35), 41000)
    qs = {f"{v:.2f}": SG.corner_params(v, timing) for v in TR.VTH_GRID}
    rows = []
    for k in splits:
        j = json.loads((OUT / f"d_T{T1}_W{WM}_{mode}_{cfg}_{k:02d}.json").read_text())
        mm = metrics(np.array(j["F"]), np.array(TR.SPL["cv_T"][k]["val"]), dies, qs)
        mm.update(split=k); rows.append(mm)
    return rows


def agg_subset(rows):
    n = sum(r["n"] for r in rows)
    out = {f"A_{k}": round(sum(r[k] for r in rows) / n, 4) for k in ("nom", "mm", "mm20", "mm35", "rt")}
    out["S"] = round(0.5 * out["A_nom"] + 0.25 * out["A_mm"] + 0.25 * out["A_rt"], 4)
    out["rt_by_vth"] = {v: round(sum(r["rt_by_vth"][v] for r in rows) / n, 4) for v in rows[0]["rt_by_vth"]}
    return out


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    mode, cfg = best_c()
    if sys.argv[1] == "screen":
        rep0 = [k for k, sp in enumerate(TR.SPL["cv_T"]) if sp["repeat"] == 0]
        jobs = [(T1, WM, k, mode, cfg) for T1, WM in GRID for k in rep0]
        with Pool(int(sys.argv[2]) if len(sys.argv) > 2 else 4) as p:
            for i, r in enumerate(p.imap_unordered(job, jobs), 1):
                print(f"[{i}/{len(jobs)}] T1 {r['T1']} WMIN {r['WMIN']} split {r['split']} wall {r['wall_s']}", flush=True)
        res = {f"T{T1}_W{WM}": agg_subset(evaluate(T1, WM, mode, cfg, rep0)) for T1, WM in GRID}
        best = max(res, key=lambda k: (res[k]["S"], k == "T170_W20", -int(k.split("_")[0][1:])))
        out = dict(c_config=dict(mode=mode, config=cfg), splits=rep0, results=res, best=best)
        (W.SUMM / "A1_d_screen.json").write_text(json.dumps(out, indent=1))
        for k, v in res.items():
            print(k, v)
        print("best", best)
    elif sys.argv[1] == "cv":
        T1, WM = int(sys.argv[2]), int(sys.argv[3])
        jobs = [(T1, WM, k, mode, cfg) for k in range(len(TR.SPL["cv_T"]))]
        with Pool(int(sys.argv[4]) if len(sys.argv) > 4 else 4) as p:
            list(p.imap_unordered(job, jobs))
        rows = evaluate(T1, WM, mode, cfg, range(len(TR.SPL["cv_T"])))
        out = dict(T1=T1, WMIN=WM, c_config=dict(mode=mode, config=cfg), cv=aggregate(rows))
        (W.SUMM / "A1_d_cv.json").write_text(json.dumps(out, indent=1))
        print(json.dumps(out, indent=1))
    elif sys.argv[1] in ("spice", "check"):
        import runs as R
        from calib_stages import K
        from calib_fit import agreement
        T1, WM = int(sys.argv[2]), int(sys.argv[3])
        timing = dict(T1=float(T1), WMIN=float(WM))
        F = np.load(W.WEIGHTS / "cand_d.npy")
        q = SG.corner_params(0.65, timing)
        w, gap, r, c1 = SG.predict(F, W.XTR[K], q)
        g = dict(zip(K, gap[0])); samples = []
        for c in range(5):                       # W13 rule under cand_d at its timing
            pool = sorted([i for i in K if W.YTR[i] == c], key=lambda i: (g[i], i)); rest = pool[2:]
            samples += pool[:2] + [rest[int(round(0.3 * (len(rest) - 1)))], rest[int(round(0.7 * (len(rest) - 1)))]]
        samples = sorted(samples)
        tag = R.timing_tag(dict(W.TIMING0, **timing))
        if sys.argv[1] == "spice":
            if not (W.SUMM / f"warm_cand_d_{tag}.json").exists():
                R.warm("cand_d", timing=dict(W.TIMING0, **timing))
            R.run_pool(R.nominal_jobs("cand_d", samples, "K", timing=dict(W.TIMING0, **timing), wtag=tag), 4)
            R.run_pool(R.nominal_jobs("cand_d", R.SPL["S"], "S", timing=dict(W.TIMING0, **timing), wtag=tag), 4)
        else:
            runs = W.load_runs(f"K_cand_d_{tag}")
            ag = agreement(runs, q)
            out = dict(T1=T1, WMIN=WM, samples=samples, agreement={k: v for k, v in ag.items() if k != "rows"}, rows=ag["rows"],
                       admitted=ag["first_agree"] >= 17, trips_in_C1=sum(1 for m in runs if m.get("trip_in_C1")))
            (W.SUMM / "A1_d_check.json").write_text(json.dumps(out, indent=1, default=float))
            print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1, default=float))
    elif sys.argv[1] == "final":
        T1, WM = int(sys.argv[2]), int(sys.argv[3])
        if not (TR.JOBS / f"a_{mode}_{TR.A_START_M:g}_-1.json").exists():
            TR.job(("a", mode, TR.A_START_M, -1))
        r = job((T1, WM, -1, mode, cfg))
        np.save(W.WEIGHTS / "cand_d.npy", np.array(r["F"]))
        print(json.dumps({k: v for k, v in r.items() if k != "info"}, indent=1))
