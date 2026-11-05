"""B3: V_th-learning methods under Monte Carlo (DECISIONS E8). PROXY/ASSUMED spreads.
Dies: anchors 20 and 35 mV, size-scaled V_th mismatch (common.apply_mc scale='pelgrom_vth', mu and R_C nominal),
10 dies per anchor, die seed = 1000*anchor + die (dies 1-5 share their V_th draws with fitc10 3B-V). Global |V_th| per
die: stratified uniform over 0.55-0.95 V (one die per 40 mV stratum, order and position from default_rng(9000+anchor)).
Methods (vthmeth.py): rep (replica TFT, Variant 3R), a1 (host supply current), a2 (two-step race timing), plus
ideal (levels from the true global |V_th|). Each estimate is offset-corrected with its nominal-die value.
Stages:  offsets | est | cls [nproc]   -> raw/b3/, summary/b3_offsets.json, summary/b3_estimates.json"""
import json, sys
from multiprocessing import Pool
import numpy as np
import eh, vthmeth as M

OUT = eh.RAW / "b3"   # B4 estimate runs also land here (prefix g<vth>_m<mu>)
ANCHORS, DIES = (20, 35), tuple(range(1, 11))
METHODS = ("ideal", "a1", "a2", "rep")
OFFS_F, EST_F = eh.SUMM / "b3_offsets.json", eh.SUMM / "b3_estimates.json"


def die(a, d):
    rng = np.random.default_rng(9000 + a)
    perm, u = rng.permutation(10), rng.random(10)
    g = round(0.55 + 0.04 * (perm[d - 1] + u[d - 1]), 4)
    seed = 1000 * a + d
    sig_rep = a / 1000 * np.sqrt(780.0 / (M.REP_W * M.REP_L))
    rep_dvth = float(np.random.default_rng([seed, 1]).normal(0, sig_rep))   # replica: own stream, classifier draws unchanged
    return dict(anchor=a, die=d, seed=seed, g=g, rep_dvth=rep_dvth, rep_sigma=float(sig_rep),
                mc=dict(seed=seed, s_vth=a / 1000, s_mu=0.10, s_rc=0.20, scale="pelgrom_vth"))


def _a1(args):
    tag, vth, muf, mc = args
    f = OUT / "a1" / f"{tag}.json"
    return json.load(open(f)) if f.exists() else M.supply(tag, OUT / "a1", vth=vth, muf=muf, mc=mc)


def a2_two_step(prefix, vth, muf, mc, off, pool):
    """Returns dict(step1, step2, vth_est). off = (offset1, offset2) or None (nominal calibration: raw values)."""
    j1 = M.race_jobs(f"{prefix}_st1", OUT / "a2", vth=vth, muf=muf, mc=mc, V2s=M.RACE_V2_STEP1)
    r1 = list(pool.map(eh.run_cached, j1))
    e1 = M.race_estimate(r1[0], r1[1], M.RACE_V2_STEP1)
    o1 = off[0] if off else 0.0
    est1 = e1["vth_raw"] - o1 if e1["vth_raw"] is not None else None
    if est1 is None:
        return dict(step1=e1, step2=None, vth_est=None)
    V2s = M.race2_step2_levels(est1 if off else 0.65)   # nominal calibration: step 2 at the true nominal |V_th|
    j2 = M.race_jobs(f"{prefix}_st2", OUT / "a2", vth=vth, muf=muf, mc=mc, V2s=V2s)
    r2 = list(pool.map(eh.run_cached, j2))
    e2 = M.race_estimate(r2[0], r2[1], V2s)
    e2["V2s"] = V2s
    o2 = off[1] if off else 0.0
    return dict(step1=e1, est1=est1, step2=e2, vth_est=(e2["vth_raw"] - o2) if e2["vth_raw"] is not None else None)


def offsets(n=4):
    """Design-time offsets on the nominal die (|V_th| 0.65 V, mu x1, no mismatch)."""
    if OFFS_F.exists():
        return json.load(open(OFFS_F))
    with Pool(n) as p:
        rep = M.replica(0.65, 1.0, 0.0, tag="rep_nom")
        a1 = _a1(("a1_nom", 0.65, 1.0, None))
        a2 = a2_two_step("a2_nom", 0.65, 1.0, None, None, p)
    res = dict(rep=rep["vth_raw"] - 0.65, a1=a1["vth_raw"] - 0.65, a2=[a2["step1"]["vth_raw"] - 0.65, a2["step2"]["vth_raw"] - 0.65],
               raw=dict(rep=rep, a1={k: a1[k] for k in ("vth_raw", "vsg_at_I", "I_base_uA")}, a2=a2))
    json.dump(res, open(OFFS_F, "w"), indent=1, default=float)
    return res


def estimate(dd, off, pool, vth=None, muf=1.0, prefix=None):
    """All three estimates for one die (vth defaults to the die's global |V_th|)."""
    vth = dd["g"] if vth is None else vth
    prefix = prefix or f"an{dd['anchor']:02d}_d{dd['die']:02d}"
    rep = M.replica(vth, muf, dd["rep_dvth"], tag=f"rep_{prefix}")
    a1 = pool.apply_async(_a1, ((f"a1_{prefix}", vth, muf, dd["mc"]),))
    a2 = a2_two_step(f"a2_{prefix}", vth, muf, dd["mc"], off["a2"], pool)
    a1 = a1.get()
    return dict(rep=dict(vth_est=rep["vth_raw"] - off["rep"], raw=rep),
                a1=dict(vth_est=(a1["vth_raw"] - off["a1"]) if a1["vth_raw"] is not None else None, raw=a1["vth_raw"],
                        vsg_at_I=a1["vsg_at_I"], na_max=max((x for x in a1["na_max_during_ramp"].values() if x is not None), default=None),
                        failed=a1.get("failed", False)),
                a2=dict(vth_est=a2["vth_est"], step1_t=a2["step1"]["t_us"], est1=a2.get("est1"),
                        step2_t=(a2["step2"] or {}).get("t_us"), step2_V2=(a2["step2"] or {}).get("V2s")))


def est_all(n=4):
    off = json.load(open(OFFS_F))
    res = json.load(open(EST_F)) if EST_F.exists() else {}
    with Pool(n) as p:
        for a in ANCHORS:
            for d in DIES:
                k = f"an{a:02d}_d{d:02d}"
                if k in res:
                    continue
                dd = die(a, d)
                res[k] = dict(die=dd, **estimate(dd, off, p))
                print(k, dd["g"], {m: res[k][m]["vth_est"] for m in ("rep", "a1", "a2")}, flush=True)
                json.dump(res, open(EST_F, "w"), indent=1, default=float)
    return res


def cls_jobs():
    est = json.load(open(EST_F))
    js = []
    for a in ANCHORS:
        for d in DIES:
            k = f"an{a:02d}_d{d:02d}"
            dd = est[k]["die"]
            for meth in METHODS:
                v = dd["g"] if meth == "ideal" else est[k][meth]["vth_est"]
                if v is None:
                    continue
                V1, V2 = (round(x, 3) for x in eh.formula_levels(v))
                js += [dict(tag=f"M_{k}_L{round(V1*1000):04d}_{round(V2*1000):04d}_s{i:02d}", idx=i, outdir=OUT / "cls", wdir="b3",
                            vth=dd["g"], mc=dd["mc"], V1=V1, V2=V2, inst=False, vth_metric=dd["g"], method=meth, die_key=k)
                       for i in eh.SUB]
    return js


if __name__ == "__main__":
    w = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    if w == "offsets":
        print(json.dumps(offsets(n), indent=1, default=float))
    elif w == "est":
        est_all(n)
    elif w == "cls":
        eh.pool_run(cls_jobs(), n)
