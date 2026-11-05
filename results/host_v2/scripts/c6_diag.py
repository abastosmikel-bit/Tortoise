"""C6 diagnostic (after the freeze; analysis only, no protocol change): where is the stuck-latch edge under v2, and which
v2 element moves it? Short runs of #81 to 330 us (the latch state at the start of trip counting is input-independent,
the energy/host study's E6), fixed levels 1.82/2.40 V, k = 1. 'stuck' = any na > 1.65 V at 320 us (energy/host study definition).
Variants: v2 (1 s-off start state of the nominal calibration, rstb 50) | zero (all-zero start, rstb 50) |
v2_rstb150 (1 s-off start, rstb 150) | zero_rstb150 (all-zero start, rstb 150 = energy/host study O2 timing).
-> raw/C6diag/*.json, summary/c6_diag.json"""
import json, sys
from multiprocessing import Pool
import numpy as np
import hv2, eh, common as C

OUT = hv2.RAW / "C6diag"
GRID = [round(0.50 + 0.01 * k, 2) for k in range(18)]   # 0.50 ... 0.67
NODES = [f"na{k}" for k in range(1, 6)] + [f"d{k}" for k in range(1, 6)] + ["vls", "ref", "ap1", "nb1"]


def short(args):
    var, vth = args
    tag = f"D_{var}_v{round(vth*1000):04d}"
    f = OUT / f"{tag}.json"
    if f.exists():
        return json.load(open(f))
    OUT.mkdir(parents=True, exist_ok=True)
    wd = C.workdir("hv2_c6d")
    net = wd / f"{tag}.cir"
    eh.build(net, 81, vth=vth, inst=False, cold=True, rstb_rel=None if var.endswith("rstb150") else 50.0, t_end=330.0)
    if var.startswith("v2"):
        st = json.load(open(hv2.CAL / "v0650_m100/calibration.json"))["start_state"]
        t = net.read_text()
        import re
        t = re.sub(r"^\.ic .*$", hv2.ic_line(st), t, flags=re.M)
        net.write_text(t)
    d, info = hv2.simulate(net, tag, [f"v({n})" for n in NODES])
    net.unlink()
    at = lambda n, x: round(float(np.interp(x * 1e-6, d["time"], d[f"v({n})"])), 4)
    r = dict(tag=tag, variant=var, vth=vth, run=info, **{f"{n}@{x}": at(n, x) for n in NODES for x in (50, 150, 300, 311, 320)})
    r["na_max@320"] = max(r[f"na{k}@320"] for k in range(1, 6))
    r["stuck"] = r["na_max@320"] > 1.65
    f.write_text(json.dumps(r, indent=1))
    return r


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    jobs = [(v, x) for v in ("v2", "zero", "v2_rstb150", "zero_rstb150") for x in GRID]
    with Pool(n) as p:
        res = p.map(short, jobs)
    out = {}
    for v in ("v2", "zero", "v2_rstb150", "zero_rstb150"):
        rr = sorted([r for r in res if r["variant"] == v], key=lambda r: r["vth"])
        st = [r["vth"] for r in rr if r["stuck"]]
        out[v] = dict(highest_stuck=max(st) if st else None,
                      lowest_working_above=min([r["vth"] for r in rr if not r["stuck"] and (not st or r["vth"] > max(st))], default=None),
                      grid={f"{r['vth']:.2f}": dict(stuck=r["stuck"], na_max_320=r["na_max@320"], d1_311=r["d1@311"],
                                                    vls_311=r["vls@311"], ref_311=r["ref@311"], ref_50=r["ref@50"]) for r in rr})
    json.dump(out, open(hv2.SUMM / "c6_diag.json", "w"), indent=1)
    for v, o in out.items():
        print(v, o["highest_stuck"], o["lowest_working_above"])
