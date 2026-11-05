"""T8 = T6 + latch reset by nb pull-up + long reset prefix T1 (rows inactive), optional warm start."""
import re, sys
sys.path.insert(0, 'tools'); sys.path.insert(0, '../tools')
from t6fix import fix
WARM = (".ic v(ref)=0.8 v(ap1)=2.0 v(ap2)=1.8 v(ap3)=1.7 v(ap4)=1.6 v(ap5)=1.5\n"
        "+ v(na1)=3.1 v(na2)=0.8 v(na3)=0.8 v(na4)=0.8 v(na5)=0.8\n"
        "+ v(nb1)=0.6 v(nb2)=3.1 v(nb3)=3.1 v(nb4)=3.1 v(nb5)=3.1\n"
        "+ v(win)=3.3 v(vboot)=0.0 v(lockb)=0.9")
SAMPLE_IN_RESET = False
def t8(src, dst, x, T1=300e-6, tC=2500e-6, warm=False, low=0.0):
    t = fix(open(src).read(), x, tC, tC + 100e-6)      # T6 fixes (ramps etc.), then shift everything by T1
    o = T1 * 1e6; L = f"{low:.2f}"
    def sub(p, r, n=1):
        nonlocal t; t, k = re.subn(p, r, t, flags=re.M); assert k == n, (p, k)
    sub(r"^V_RSTB\s.*$", f"V_RSTB rstb 0 PWL(0 {L} {o+1:.1f}u {L} {o+2:.1f}u 3.3)")
    sub(r"^V_RSTR\s.*$", f"V_RSTR rstr 0 PWL(0 {L} {o+11.5:.1f}u {L} {o+12.5:.1f}u 3.3)")
    if SAMPLE_IN_RESET:   # T9: sampling switches on from t=0, released with rstr
        sub(r"^V_PHIB\s.*$", f"V_PHIB phib 0 PWL(0 {L} {o+11.5:.1f}u {L} {o+12.5:.1f}u 3.3)")
        sub(r"^V_PHI\s.*$",  f"V_PHI phi 0 PWL(0 3.3 {o+11.5:.1f}u 3.3 {o+12.5:.1f}u {L})")
    else:
        sub(r"^V_PHIB\s.*$", f"V_PHIB phib 0 PWL(0 3.3 {o+1:.1f}u 3.3 {o+2:.1f}u {L} {o+11.5:.1f}u {L} {o+12.5:.1f}u 3.3)")
        sub(r"^V_PHI\s.*$",  f"V_PHI phi 0 PWL(0 {L} {o+1:.1f}u {L} {o+2:.1f}u 3.3 {o+11.5:.1f}u 3.3 {o+12.5:.1f}u {L})")
    te = o + tC * 1e6
    for i, b in enumerate(x, 1):
        w = (f"PWL(0 3.3 {o+1:.1f}u 3.3 {o+2:.1f}u 1.62 {te:.1f}u 1.62 {te+1:.1f}u 3.3)" if b
             else f"PWL(0 3.3 {o+1:.1f}u 3.3 {o+2:.1f}u 1.62 {o+10:.1f}u 1.62 {o+11:.1f}u 3.3)")
        sub(rf"^(VR{i}\s+row{i}\s+0\s+).*$", rf"\g<1>{w}")
    for c in range(1, 6):
        sub(rf"^X{88+10*(c-1)}\s+0\s+rstr\s+na{c}\s+potft", f"X{88+10*(c-1)} nb{c} rstr vdd potft")
    sub(r"^\.tran .*$", f".tran 100n {o + tC*1e6 + 100:.0f}u 0 100n")
    if warm:
        i = t.index('.ic '); j = t.index('\n', t.index('v(win)=', i)); t = t[:i] + WARM + t[j:]
    open(dst, "w").write(t)
if __name__ == "__main__":
    src, dst, xs = sys.argv[1:4]; warm = "warm" in sys.argv; low = float(next((a[4:] for a in sys.argv if a.startswith("low=")), 0))
    SAMPLE_IN_RESET = "t9" in sys.argv
    t8(src, dst, [int(c) for c in xs], warm=warm, low=low)
