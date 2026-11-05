"""T6 = T5 + M88 40/5 + 1 us ramps on control and row edges + win reset-precharge (+1 TFT) + CWIN 2 pF."""
import re, sys
def fix(txt, x, tC_end, t_sim):
    def sub(p, r, n=None):
        nonlocal txt; txt, k = re.subn(p, r, txt, flags=re.M); assert k > 0 and (n is None or k == n), p
    for c in range(1, 6):
        sub(rf"^(X{88+10*(c-1)}\s+0\s+rstr\s+na{c}\s+potft\s+)W=150", r"\g<1>W=40", 1)
    sub(r"^CWIN\s+win\s+0\s+0\.20p", "CWIN win 0 2p\nXWR win rstr vdd potft W=10 L=5   $ precharge win high during reset (keeps win >= 0)", 1)
    sub(r"^V_RSTB\s.*$", "V_RSTB       rstb       0 PWL(0 0 1.0u 0 2.0u 3.3)", 1)
    sub(r"^V_RSTR\s.*$", "V_RSTR       rstr       0 PWL(0 0 11.5u 0 12.5u 3.3)", 1)
    sub(r"^V_PHIB\s.*$", "V_PHIB       phib       0 PWL(0 3.3 1.0u 3.3 2.0u 0 11.5u 0 12.5u 3.3)", 1)
    sub(r"^V_PHI\s.*$",  "V_PHI        phi        0 PWL(0 0 1.0u 0 2.0u 3.3 11.5u 3.3 12.5u 0)", 1)
    sub(r"v\(win\)=0 ", "v(win)=3.3 ", 1)
    te = tC_end * 1e6
    for i, b in enumerate(x, 1):
        w = (f"PWL(0 3.3 1.0u 3.3 2.0u 1.62 {te:.1f}u 1.62 {te+1:.1f}u 3.3)" if b
             else "PWL(0 3.3 1.0u 3.3 2.0u 1.62 10.0u 1.62 11.0u 3.3)")
        sub(rf"^(VR{i}\s+row{i}\s+0\s+).*$", rf"\g<1>{w}", 1)
    sub(r"^\.tran .*$", f".tran 100n {t_sim*1e6:.0f}u 0 100n", 1)
    return txt
if __name__ == "__main__":
    src, dst, xs, tc, ts = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), float(sys.argv[5])
    open(dst, "w").write(fix(open(src).read(), [int(c) for c in xs], tc, ts))
