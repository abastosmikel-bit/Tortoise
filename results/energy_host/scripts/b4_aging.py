"""B4: aging map (PROXY inputs, DECISIONS E7). Global dV_th in {0, +0.10, +0.20, +0.30, +0.35} V from 0.65 V x mobility factor
{1, 0.85, 0.70, 0.60, 0.50}. 20-sample subset, Variant 3 warm start (nominal end state for every cell: approximation),
2500 us window, not instrumented. Trim policies:
  none   : levels fixed at the 0.65 V values (1.82 / 2.40 V)
  ideal  : formula levels for the cell's true |V_th|
  <meth> : formula levels for the method's estimate on that aged die (estimates in summary/b4_estimates.json)
Runs are tagged by (corner, V1, V2, timing), so a configuration shared by several policies is simulated once.
Usage: python3 b4_aging.py none|ideal|<method>|timing:<variant> [nproc]"""
import json, sys
import eh

OUT = eh.RAW / "b4_aging"
DV = (0.0, 0.10, 0.20, 0.30, 0.35)
MU = (1.0, 0.85, 0.70, 0.60, 0.50)
CELLS = [(round(0.65 + d, 2), m) for d in DV for m in MU]
CELLS3 = [(round(0.65 + d, 2), m) for d in (0.0, 0.20, 0.35) for m in (1.0, 0.70, 0.50)]   # E10 scope cut


def tag(vth, muf, V1, V2, i, tim=""):
    return f"G_v{round(vth*100):03d}_m{round(muf*100):03d}_L{round(V1*1000):04d}_{round(V2*1000):04d}{tim}_s{i:02d}"


def job(vth, muf, V1, V2, i, policy, **tk):
    tim = "".join(f"_{k}{v:g}" for k, v in sorted(tk.items()))
    return dict(tag=tag(vth, muf, V1, V2, i, tim), idx=i, outdir=OUT, wdir="b4", vth=vth, muf=muf, V1=V1, V2=V2,
                inst=False, vth_metric=vth, policy=policy, **tk)


def levels(policy, vth, muf):
    if policy == "none":
        return eh.formula_levels(0.65)
    if policy == "ideal":
        return eh.formula_levels(vth)
    est = json.load(open(eh.SUMM / "b4_estimates.json"))[f"{vth:.2f}_{muf:.2f}"][policy]["vth_est"]
    return tuple(round(x, 3) for x in eh.formula_levels(est))


def jobs(policy, cells=CELLS, **tk):
    js = []
    for v, m in cells:
        V1, V2 = levels(policy, v, m)
        js += [job(v, m, V1, V2, i, policy, **tk) for i in eh.SUB]
    return js


if __name__ == "__main__":
    pol = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 4
    if pol.startswith("timing:"):
        import b4_timing
        js = b4_timing.jobs(pol.split(":")[1])
    else:
        js = jobs(pol, cells=CELLS3) if "--3x3" in sys.argv else jobs(pol)
    eh.pool_run(js, n)
