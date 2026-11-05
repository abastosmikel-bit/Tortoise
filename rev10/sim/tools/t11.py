"""T11 = T10 with retrained crossbar widths (W = 10 um x fingers) and duty-cycle pulsed rows.
Rows: inactive during reset, all active in phase B, then from release each row is at 1.62 V for
x_i/m of every period P (0.2 us edges; on-time measured edge-midpoint to edge-midpoint)."""
import re, sys, numpy as np
sys.path.insert(0, 'tools'); sys.path.insert(0, '../tools')
from t10 import t10
import os
F = np.load(os.environ.get("FINGERS", "/home/claude/w/repo/data/trace2_fingers_retrained.npy")).astype(int)
def row_pwl(x, o, t0, tend, m, P, tr=None):
    tr = float(os.environ.get("EDGE", 0.2)) if tr is None else tr
    pts = [(0, 3.3), (o + 1, 3.3), (o + 2, 1.62), (o + 10, 1.62), (o + 11, 3.3)]
    on = x / m * P
    if on >= 0.1:
        t = t0
        while t + P <= tend:
            hold = max(on - tr, 0.0); r = min(tr, on)          # short pulses become triangles
            pts += [(t, 3.3), (t + r, 1.62), (t + r + hold, 1.62), (t + 2*r + hold, 3.3)]  # r = edge time
            t += P
    return "PWL(" + " ".join(f"{a:.3f}u {b}" for a, b in pts) + ")"
def t11(dst, x, prior, t_pred_us, m=4, P=40.0, T1=300e-6, base="t5L_x2_v085.cir"):
    n = t10(base, dst, [1]*6, prior, T1=T1, tC=3000e-6)
    t = open(dst).read(); o = T1 * 1e6; t0 = o + 12.5; tend = t0 + t_pred_us + 200
    for k in range(5):
        for i in range(6):
            dn = 1 + 6*k + i; W = 10 * F[i, k]
            pat = rf"^(X{dn}\s+ap{k+1}\s+row{i+1}\s+vdd\s+potft\s+)W=\S+(\s+L=54)"
            if W > 0: t, c = re.subn(pat, rf"\g<1>W={W}\g<2>", t, flags=re.M)
            else:     t, c = re.subn(pat + r".*$", rf"* X{dn} removed: 0 fingers", t, flags=re.M)
            assert c == 1, (dn, c)
    for i in range(6):
        t, c = re.subn(rf"^(VR{i+1}\s+row{i+1}\s+0\s+).*$", rf"\g<1>{row_pwl(x[i], o, t0, tend, m, P)}", t, flags=re.M); assert c == 1
    t, c = re.subn(r"^\.tran .*$", f".tran 100n {tend:.0f}u 0 100n", t, flags=re.M); assert c == 1
    open(dst, "w").write(t)
    return tend
if __name__ == "__main__":
    idx = int(sys.argv[1]); prior = sys.argv[2]; tp = float(sys.argv[3])
    d = np.load("/home/claude/w/repo/data/trace2_data.npz")
    print("sim end", t11(os.environ.get("OUT", f"t11_s{idx}.cir"), d["X_test"][idx], prior, tp), "us")
