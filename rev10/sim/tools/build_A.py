"""FINAL design driven by scheme A (integrate, then race) with pedestal, crossbar on the segmented-channel model."""
import os, sys, re, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_final as BF
def build(dst, x, prior, vth="085", T1=170.0, WMIN=20.0, GAP=5.0, V2=None, TRACE=900.0, seg=True, die_seed=None, V1=None):
    vt = int(vth) / 100.0
    V1 = round(3.3 - vt - 0.83, 3) if V1 is None else V1   # Vth-referenced C1 / calibration level
    V2 = round(3.3 - vt - 0.25, 3) if V2 is None else V2   # Vth-referenced C2 ramp level
    BF.build(dst, x, prior, 1000, vth, 4, die_seed)
    t = open(dst).read(); o = 300.0; t0 = o + 12.5; tr = 0.2
    tC2 = t0 + WMIN + T1 + GAP
    for i in range(6):
        w = WMIN + x[i] * T1
        pwl = (f"PWL(0 3.3 {o+1:.1f}u 3.3 {o+2:.1f}u {V1} {o+10:.1f}u {V1} {o+11:.1f}u 3.3 "
               f"{t0:.2f}u 3.3 {t0+tr:.2f}u {V1} {t0+w:.2f}u {V1} {t0+w+tr:.2f}u 3.3 "
               f"{tC2:.2f}u 3.3 {tC2+tr:.2f}u {V2})")
        t, n = re.subn(rf"^(VR{i+1}\s+row{i+1}\s+0\s+).*$", rf"\g<1>{pwl}", t, flags=re.M); assert n == 1
    # NAPRE: equalise latch history - precharge every na high during early reset (rstb low), release rstb at 150 us
    add = "\n".join(f"XNP{c} na{c} rstb vdd potft W=20 L=5   $ na precharge (history equaliser)" for c in range(1, 6))

    t, n = re.subn(r"^(CWIN .*)$", r"\g<1>\n" + add, t, flags=re.M); assert n == 1
    t, n = re.subn(r"^V_RSTB\s.*$", "V_RSTB rstb 0 PWL(0 0 150u 0 151u 3.3)", t, flags=re.M); assert n == 1
    # RESET_SCALE: rail reset switches 100/5 -> 400/20 (same W/L, 16x area -> reset-level offset sigma /4)
    t, n = re.subn(r"^(X7[5-9]\s+0\s+rstr\s+ap\d\s+potft\s+)W=100\s+L=5", r"\g<1>W=400 L=20", t, flags=re.M); assert n == 5, n
    if die_seed is not None:   # rescale DVTH of the resized reset switches by sqrt(500/8000) (Pelgrom), keep json in sync
        import json
        jf = dst.replace(".cir", "_dvth.json"); dvj = json.load(open(jf))
        def rs(mo):
            v = float(mo.group(2)) * (500 / 8000) ** 0.5; dvj[mo.group(1).split()[0]] = v
            return f"{mo.group(1)}DVTH={v:.5f}"
        t, n = re.subn(r"^(X7[5-9]\s+0\s+rstr\s+ap\d\s+potft\s+W=400\s+L=20\s+)DVTH=(\S+)", rs, t, flags=re.M); assert n == 5, n
        json.dump(dvj, open(jf, "w"), indent=0)
    if seg:
        t, n = re.subn(r"^(X\d+\s+ap\d\s+row\d\s+vdd\s+)potft(\s)", r"\g<1>potftseg\g<2>", t, flags=re.M); assert n >= 15, n
        t = t.replace(".include ../models/trace2_otft_v2.sub", ".include ../models/trace2_otft_v2.sub\n.include ../models/trace2_otft_seg.sub", 1)
    t, n = re.subn(r"^\.tran .*$", f".tran 100n {tC2 + TRACE:.0f}u 0 100n", t, flags=re.M); assert n == 1
    open(dst, "w").write(t)
    return tC2
if __name__ == "__main__":
    d = np.load("/home/claude/w/repo/data/trace2_data.npz")
    idx, prior = int(sys.argv[1]), sys.argv[2]; vth = os.environ.get("VTH", "085")
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else None
    print("C2 starts at", build(os.environ.get("OUT", f"A_s{idx}.cir"), d["X_test"][idx], prior, vth=vth, die_seed=seed), "us")
