"""B2: re-trim tolerance. |V_th| 0.65 V (nominal corner, formula levels 1.82/2.40 V) and 0.85 V (corner eh_v08500_m10000,
same parameters as fitc10_sweep fc10_vth085; formula levels 1.62/2.20 V). 20-sample subset, Variant 3 warm start,
2500 us window, not instrumented.
 1D: V1 offset -200..+200 mV in 25 mV steps with V2 at the formula value, and V2 offset likewise with V1 at the formula
     value (V1 is the calibration + C1 level, V2 the C2 level; DECISIONS E4).
 2D: the diagonal dV1 = dV2 (-200..+200 mV, 25 mV) and the coarse grid declared in DECISIONS E5 (E5_GRID below).
Usage: python3 b2_retrim.py 1D|2D [nproc]   -> raw/b2_retrim/<tag>.json"""
import sys
import eh

OUT = eh.RAW / "b2_retrim"
VTHS = (0.65, 0.85)
OFFS = [o for o in range(-200, 201, 25)]
E5_GRID = None   # filled in from DECISIONS E5 before the 2D run: {vth: (list of dV1 mV, list of dV2 mV)}


def tag(vth, d1, d2, i):
    return f"R_v{round(vth*100):03d}_a{d1:+04d}_b{d2:+04d}_s{i:02d}"


def job(vth, d1, d2, i):
    V1, V2 = eh.formula_levels(vth)
    return dict(tag=tag(vth, d1, d2, i), idx=i, outdir=OUT, wdir="b2", vth=vth, V1=V1 + d1 / 1000, V2=V2 + d2 / 1000,
                inst=False, vth_metric=vth, offsets_mV=[d1, d2])


def jobs_1d():
    cfg = sorted({(v, o, 0) for v in VTHS for o in OFFS} | {(v, 0, o) for v in VTHS for o in OFFS})
    return [job(v, a, b, i) for v, a, b in cfg for i in eh.SUB]


def jobs_1d50():
    """E10: 1D sweeps at 50 mV steps only."""
    return [j for j in jobs_1d() if all(o % 50 == 0 for o in j["offsets_mV"])]


def jobs_2d():
    js = [job(v, -d, -d, i) for v in VTHS for d in OFFS for i in eh.SUB]   # diagonal
    for v, (g1, g2) in E5_GRID.items():
        js += [job(v, a, b, i) for a in g1 for b in g2 for i in eh.SUB]
    return js


if __name__ == "__main__":
    mode = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    js = {"1D": jobs_1d, "1D50": jobs_1d50, "2D": jobs_2d}[mode]()
    # order: interleave so partial results cover the whole sweep early (zero offsets first)
    js.sort(key=lambda j: (abs(j["offsets_mV"][0]) + abs(j["offsets_mV"][1]) > 0, abs(j["offsets_mV"][0]) + abs(j["offsets_mV"][1]) , j["tag"]))
    eh.pool_run(js, n)
