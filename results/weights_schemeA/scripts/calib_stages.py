"""Calibration SPICE stages W4.3-W4.5 (old weights, training samples in K only, old-weights warm start raw/warm_old/warm).
Usage: python3 calib_stages.py <sens|mm|retrim> [nproc]   (resumable)
 sens   : one sample = the valid, correctly classified K run with the largest runner-up gap. Its winner's class chain:
          +30 mV on the reset switch X75+c, sense X81+10c, detect load X82+10c, trip driver X83+10c, latch devices
          X84..X87+10c, and on the winner column's largest crossbar bank; -30 mV on the sense device and the reset
          switch. 11 runs.                                                             -> raw/sens_old/
 mm     : 3 dies (size-scaled V_th only, anchor 35 mV, apply_mc_paired seeds 35101-35103) x 10 K samples: per class
          the K sample with the median old-weights margin and the one with the smallest |margin|.   -> raw/mm_old/
 colsum : W13 check of the surrogate on unequal column sums: weights/probe_le60.npy, own warm start, 20 K samples
          (per class the 2 smallest predicted gaps and the 30/70 % gap quantiles)            -> raw/K_probe_le60/
 retrim : 8 K samples (2 with the largest and 2 with the smallest max column score x.F_old, 4 at the 20/40/60/80 %
          quantiles of the rest) at re-trimmed |V_th| 0.55/0.75/0.85/0.95 V (fc10_vthXXX, build_A level formula).
                                                                                       -> raw/retrim_old/"""
import json, sys
import numpy as np
import wcommon as W
from runs import run_pool, warm_prior, SPL

K = SPL["K"]
F = W.F_OLD
PRIOR = warm_prior("old")


def sens_jobs():
    Kr = W.load_runs("K_old")
    ok = [m for m in Kr if m.get("valid") and m["winner"] == m["label"] and m.get("gap")]
    base = max(ok, key=lambda m: (m["gap"]["gap_reach_us"], -m["idx"]))
    c = base["winner"] - 1
    bank = int(np.argmax(F[:, c]))
    devs = [(f"X{75 + c}", 0.03), (f"X{81 + 10 * c}", 0.03), (f"X{82 + 10 * c}", 0.03), (f"X{83 + 10 * c}", 0.03),
            (f"X{84 + 10 * c}", 0.03), (f"X{85 + 10 * c}", 0.03), (f"X{86 + 10 * c}", 0.03), (f"X{87 + 10 * c}", 0.03),
            (f"X{1 + 6 * c + bank}", 0.03), (f"X{81 + 10 * c}", -0.03), (f"X{75 + c}", -0.03)]
    out = W.RAW / "sens_old"
    jobs = [dict(tag=f"tr{base['idx']:03d}_{d}_{'p' if v > 0 else 'm'}{abs(v)*1000:.0f}", split="train", idx=base["idx"], F=F,
                 weights_name="old", prior=PRIOR, outdir=out, wdir="wsA_sens", perturb={d: v}) for d, v in devs]
    return jobs, dict(base_tag=base["tag"], base_idx=base["idx"], winner=base["winner"], gap_us=base["gap"]["gap_reach_us"],
                      bank=f"X{1 + 6 * c + bank}", bank_fingers=int(F[bank, c]))


def mm_samples():
    X, y = W.XTR, W.YTR
    s = X @ F; so = s.copy(); so[np.arange(len(y)), y] = -np.inf
    m = s[np.arange(len(y)), y] - so.max(1)
    out = []
    for c in range(5):
        pool = sorted([i for i in K if y[i] == c], key=lambda i: (m[i], i))
        med = pool[len(pool) // 2]
        near = min([i for i in pool if i != med], key=lambda i: (abs(m[i]), i))
        out += [med, near]
    return sorted(out)


def mm_jobs():
    out = W.RAW / "mm_old"
    return [dict(tag=f"mm_an35_d{d}_tr{i:03d}", split="train", idx=i, F=F, weights_name="old", prior=PRIOR, outdir=out,
                 wdir="wsA_mm", mc=dict(seed=35100 + d, s_vth=0.035, paired=True)) for d in (1, 2, 3) for i in mm_samples()]


def retrim_samples():
    smax = (W.XTR @ F).max(1)
    ks = sorted(K, key=lambda i: (smax[i], i))
    pick = ks[:2] + ks[-2:]
    rest = [i for i in ks if i not in pick]
    pick += [rest[int(round(q * (len(rest) - 1)))] for q in (0.2, 0.4, 0.6, 0.8)]
    return sorted(pick)


def retrim_jobs():
    out = W.RAW / "retrim_old"
    return [dict(tag=f"rt_vth{int(round(v*100)):03d}_tr{i:03d}", split="train", idx=i, F=F, weights_name="old", prior=PRIOR,
                 outdir=out, wdir="wsA_rt", vth=v, levels_vth=v, corner=("fitc10_sweep.lib", f"fc10_vth{int(round(v*100)):03d}"))
            for v in (0.55, 0.75, 0.85, 0.95) for i in retrim_samples()]


def colsum_probe_weights():
    """W13: probe procedure (le60, m = 20 us, greedy descent from the rounded LR, nominal surrogate) on all of T."""
    import optim as O, surrogate as SG
    from obj import RaceObjective, descend
    f = W.WEIGHTS / "probe_le60.npy"
    if not f.exists():
        T = np.array(SPL["T"]); X, y = W.XTR[T], W.YTR[T]
        Wt, _ = O.fit_lr(X, y, 1e-3, False, True)
        F, _ = descend(RaceObjective(X, y, [SG.corner_params(0.65)], None, tau=0.0, m=20, tie=1e-3), O.to_fingers(Wt), colsum=(50, 60))
        np.save(f, F)
    return np.load(f)


def colsum_samples(F):
    import surrogate as SG
    w, gap, r, c1 = SG.predict(F, W.XTR[K], SG.corner_params(0.65))
    g = dict(zip(K, gap[0])); out = []
    for c in range(5):
        pool = sorted([i for i in K if W.YTR[i] == c], key=lambda i: (g[i], i))
        rest = pool[2:]
        out += pool[:2] + [rest[int(round(0.3 * (len(rest) - 1)))], rest[int(round(0.7 * (len(rest) - 1)))]]
    return sorted(out)


if __name__ == "__main__":
    st = sys.argv[1]; nproc = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    if st == "sens":
        jobs, info = sens_jobs()
        (W.SUMM / "sens_selection.json").write_text(json.dumps(info, indent=1))
        print(info)
    elif st == "mm":
        jobs = mm_jobs(); print("samples", mm_samples())
    elif st == "colsum":
        import runs as Rn
        F = colsum_probe_weights(); print(F.tolist(), F.sum(0).tolist())
        if not (W.SUMM / "warm_probe_le60.json").exists():
            Rn.warm("probe_le60")
        jobs = Rn.nominal_jobs("probe_le60", colsum_samples(F), "K"); print("samples", colsum_samples(F))
    elif st == "retrim":
        jobs = retrim_jobs(); print("samples", retrim_samples())
    else:
        raise SystemExit(st)
    run_pool(jobs, nproc)
