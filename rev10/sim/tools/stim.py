"""Rewrite the row drivers for an input vector x (6 bits) and phase-C end time tC_end [s].
Phase B (1-11 us): all rows active (1.62 V). Phase C (11 us - tC_end): active rows stay 1.62 V."""
import re
def rows(txt, x, tC_end=65e-6, t_sim=None):
    for i, b in enumerate(x, 1):
        if b: w = f"PWL(0 3.3 0.99u 3.3 1.00u 1.62 {tC_end*1e6-0.01:.2f}u 1.62 {tC_end*1e6:.2f}u 3.30)"
        else: w = "PWL(0 3.3 0.99u 3.3 1.00u 1.62 10.99u 1.62 11.00u 3.30)"
        txt, n = re.subn(rf"^(VR{i}\s+row{i}\s+0\s+).*$", rf"\g<1>{w}", txt, flags=re.M); assert n == 1
    if t_sim:
        txt, n = re.subn(r"^\.tran .*$", f".tran 100n {t_sim*1e6:.0f}u 0 100n", txt, flags=re.M); assert n == 1
        txt = re.sub(r"AT=99u", f"AT={t_sim*1e6-1:.0f}u", txt)
    return txt
