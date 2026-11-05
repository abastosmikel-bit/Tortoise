"""SPICE stages of this study (all resumable: a run whose json exists is skipped).
Usage: python3 runs.py <stage> [weights_name] [nproc]
 warm  <w>   : W6 warm start for weight set <w> (weights/<w>.npy; 'old' = rev10 F_hw_m4_firstpass): D7 chain on the
               class-5 training sample in T with the largest software margin, from the lab prior t6L_x2_v085,
               until every rail reset level moves < 5 mV (max 6 runs).          -> raw/warm_<w>/, summary/warm_<w>.json
 K     <w>   : nominal runs on the calibration set K                             -> raw/K_<w>/
 S     <w>   : nominal runs on the selection set S                               -> raw/S_<w>/
 sens        : W4.3 one-device V_th perturbations (old weights)                  -> raw/sens_old/
 mm          : W4.4 3 paired dies (anchor 35 mV) x 10 K samples (old weights)    -> raw/mm_old/
 retrim      : W4.5 8 K samples x re-trimmed |V_th| 0.55/0.75/0.85/0.95 V        -> raw/retrim_old/
 timing <w> <T1> <WMIN> <V2off> : option (d) calibration runs on 16 K samples at that timing
Test-set stages live in eval_test.py / robustness.py (run only after the weights are frozen)."""
import json, sys, time
import numpy as np
from multiprocessing import Pool
import wcommon as W

SPL = json.loads((W.SUMM / "splits.json").read_text())
T, K, S = SPL["T"], SPL["K"], SPL["S"]


def weights(name):
    if name == "old":
        return W.F_OLD
    F = np.load(W.WEIGHTS / f"{name}.npy").astype(int)
    assert F.shape == (6, 5) and (F >= 0).all() and (F.sum(0) <= 60).all() and (F.sum(0) >= 50).all() and 15 <= (F > 0).sum() <= 21, F
    return F


def warm_prior(name, timing=None):
    return W.RAW / (f"warm_{name}" if timing is None else f"warm_{name}_{timing_tag(timing)}") / "warm"


def timing_tag(tm):
    return f"T{tm['T1']:g}_W{tm['WMIN']:g}_V2o{tm['V2off']:g}"


def warm(name, timing=None):
    F = weights(name)
    X, y = W.XTR, W.YTR
    s = X @ F
    so = s.copy(); so[np.arange(len(y)), y] = -np.inf
    m = s[np.arange(len(y)), y] - so.max(1)
    pool = [i for i in T if y[i] == 4]
    idx = max(pool, key=lambda i: (m[i], -i))
    out = W.RAW / (f"warm_{name}" if timing is None else f"warm_{name}_{timing_tag(timing)}")
    prior, hist = W.LAB_PRIOR, []
    for k in range(1, 7):
        tag = f"ws{k:02d}_tr{idx:03d}"
        if (out / f"{tag}.json").exists():
            mt = json.loads((out / f"{tag}.json").read_text())
        else:
            mt = W.run_one(dict(tag=tag, split="train", idx=idx, F=F, weights_name=name, prior=prior, outdir=out,
                                wdir=f"wsA_warm_{out.name}", timing=timing, save_prior=out / f"{tag}_end"))
        rl = mt["reset_level"]
        d = max(abs(rl[i] - hist[-1]["reset_level"][i]) for i in rl) * 1e3 if hist else None
        hist.append(dict(run=k, tag=tag, prior=str(prior), reset_level=rl, ref_reset=mt["ref_reset"], max_delta_mV=d,
                         latched=mt.get("latched"), valid=mt.get("valid"), trip_us=mt.get("trip_us"),
                         lock_latency_us=mt.get("lock_latency_us"), wall_s=mt["run"]["wall_s"]))
        print(json.dumps(hist[-1], default=float), flush=True)
        prior = out / f"{tag}_end"
        if d is not None and d < 5.0:
            break
    import shutil
    for ext in (".dat", ".cols"):
        shutil.copy(str(prior) + ext, str(out / "warm") + ext)
    res = dict(weights=name, timing=timing, sample_train_idx=idx, sample_label=int(y[idx]) + 1, sample_sw_margin=round(float(m[idx]), 3),
               converged=hist[-1]["max_delta_mV"] is not None and hist[-1]["max_delta_mV"] < 5.0, n_runs=len(hist),
               warm_start=str(out / "warm"), runs=hist)
    (W.SUMM / f"{out.name}.json").write_text(json.dumps(res, indent=1, default=float))
    return res


def nominal_jobs(name, idxs, sub, timing=None, wtag=None):
    F = weights(name)
    out = W.RAW / f"{sub}_{name}" if wtag is None else W.RAW / f"{sub}_{name}_{wtag}"
    return [dict(tag=f"tr{i:03d}", split="train", idx=i, F=F, weights_name=name, prior=warm_prior(name, timing), outdir=out,
                 wdir=f"wsA_{out.name}", timing=timing) for i in idxs]


def run_pool(jobs, nproc):
    jobs = [j for j in jobs if not (j["outdir"] / f"{j['tag']}.json").exists()]
    s = time.time()
    if not jobs:
        print("nothing to do"); return
    with Pool(nproc) as p:
        for k, m in enumerate(p.imap_unordered(W.run_one, jobs), 1):
            print(f"[{k}/{len(jobs)} {time.time()-s:6.0f}s] {m['tag']} label {m['label']} latched {m.get('latched')} "
                  f"valid {m.get('valid')} {m.get('failure')} gap {(m.get('gap') or {}).get('gap_reach_us')} wall {m['run']['wall_s']}", flush=True)


if __name__ == "__main__":
    st = sys.argv[1]
    if st == "warm":
        warm(sys.argv[2])
    elif st in ("K", "S"):
        run_pool(nominal_jobs(sys.argv[2], K if st == "K" else S, st), int(sys.argv[3]) if len(sys.argv) > 3 else 4)
    else:
        raise SystemExit(f"stage {st}: see calib_stages.py")
