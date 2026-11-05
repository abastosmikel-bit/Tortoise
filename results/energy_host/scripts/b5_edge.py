"""B5: the lower |V_th| edge (stuck latches). DECISIONS E6.
 short: runs to 330 us on #81 (the latch state at the start of trip counting does not depend on the input: rows are
        inactive until 301 us and calibration is input-independent). Records na1-5 at 311 us (just before rstr releases),
        312.5 us and 320 us, d, vls, ref. 'stuck' = any na > 1.65 V at 320 us.
        Fine sweep |V_th| 0.44-0.66 V in 10 mV, then bisection to 1 mV inside the bracketing step, per host policy.
 full:  20-sample accuracy runs, |V_th| 0.45-0.55 V in 10 mV, for the policies in FULL_POLICIES.
Host policies (all host-only; E6):
  fixed   : levels 1.82/2.40 V (as 3A)           formula : V1/V2 by the build_A formula for the corner |V_th|
  rstb50  : fixed levels, rstb (na precharge) released at 50 us instead of 150 us
  Vcal-X  : fixed levels except the calibration row level = 1.82 - X mV (C1 keeps V1); X = 200, 400
  rext300 : fixed levels, reset phase 300 us longer (all events from 300 us on shift by +300 us; rstb unchanged)
Usage: python3 b5_edge.py short <policy> | full <policy> [nproc]"""
import json, re, sys
import numpy as np
import eh, common as C

OUT_S, OUT_F = eh.RAW / "b5_short", eh.RAW / "b5_full"
GRID = [round(0.44 + 0.01 * k, 2) for k in range(23)]
FULL = [round(0.45 + 0.01 * k, 2) for k in range(11)]


def policy_kw(pol, vth):
    if pol == "fixed":
        return {}
    if pol == "formula":
        V1, V2 = eh.formula_levels(vth)
        return dict(V1=V1, V2=V2)
    if pol == "rstb50":
        return dict(rstb_rel=50.0)
    if pol == "rext300":
        return dict(reset_ext=300.0)
    if pol.startswith("Vcal"):
        return dict(Vcal=1.82 - int(pol.split("-")[1]) / 1000)
    raise ValueError(pol)


def short(pol, vth, tag=None):
    tag = tag or f"S_{pol}_v{round(vth * 1000):04d}"
    f = OUT_S / f"{tag}.json"
    if f.exists():
        return json.load(open(f))
    wd = C.workdir("eh_b5s")
    net = wd / f"{tag}.cir"
    kw = policy_kw(pol, vth)
    vcal = kw.get("Vcal")
    sh = kw.get("reset_ext", 0.0)
    b = eh.build(net, 81, vth=vth, t_end=330 + sh, inst=False, **kw)
    nodes = [f"na{k}" for k in range(1, 6)] + [f"nb{k}" for k in range(1, 6)] + [f"d{k}" for k in range(1, 6)] + ["vls", "ref", "ap1"]
    d, info = eh.simulate(net, tag, [f"v({n})" for n in nodes])
    net.unlink()
    tt = d["time"]
    at = lambda n, x: float(np.interp(x * 1e-6, tt, d[f"v({n})"]))
    # sample times are protocol-relative (shifted with the reset extension); labels keep the baseline times
    r = dict(tag=tag, policy=pol, vth=vth, run=info, vcal=vcal, reset_ext=sh,
             **{f"{n}@{x}": round(at(n, x + (sh if x >= 300 else 0)), 4) for n in nodes for x in (150, 300, 311, 312.5, 320)})
    r["na_max@311"] = max(r[f"na{k}@311"] for k in range(1, 6))
    r["na_max@320"] = max(r[f"na{k}@320"] for k in range(1, 6))
    r["stuck"] = r["na_max@320"] > 1.65
    OUT_S.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(r, indent=1))
    return r


def sweep(pol, nproc=4):
    from multiprocessing import Pool
    with Pool(nproc) as p:
        res = p.starmap(short, [(pol, v) for v in GRID])
    res.sort(key=lambda r: r["vth"])
    # bisection inside the highest stuck / lowest working bracket
    st = [r["vth"] for r in res if r["stuck"]]
    ok = [r["vth"] for r in res if not r["stuck"]]
    out = dict(policy=pol, grid={r["vth"]: dict(stuck=r["stuck"], na_max_311=r["na_max@311"], na_max_320=r["na_max@320"],
                                               d1_311=r["d1@311"], vls_311=r["vls@311"], ref_311=r["ref@311"]) for r in res})
    if st and ok and max(st) < min(v for v in ok if v > max(st)):
        lo, hi = max(st), min(v for v in ok if v > max(st))
        while hi - lo > 0.0011:
            mid = round((lo + hi) / 2, 4)
            if short(pol, mid)["stuck"]:
                lo = mid
            else:
                hi = mid
        out["threshold_V"] = dict(highest_stuck=lo, lowest_working=hi)
        out["monotonic"] = all(v > max(st) for v in ok if v > lo) and all(v < hi for v in st)
    json.dump(out, open(eh.SUMM / f"b5_short_{pol}.json", "w"), indent=1)
    return out


def full_jobs(pol):
    js = []
    for v in FULL + ([0.65] if pol not in ("fixed", "formula") else []):   # E6: nominal check for a host fix
        kw = policy_kw(pol, v)
        js += [dict(tag=f"F_{pol}_v{round(v*1000):04d}_s{i:02d}", idx=i, outdir=OUT_F, wdir="b5f", vth=v, inst=False,
                    vth_metric=v, **kw) for i in eh.SUB]
    return js


if __name__ == "__main__":
    w, pol = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    if w == "short":
        print(json.dumps(sweep(pol, n), indent=1))
    else:
        eh.pool_run(full_jobs(pol), n)
