"""H1.7: end-to-end calibration session on two off-grid development corners (no classification). raw/cal/dev_*."""
import json, sys
from multiprocessing import Pool
import hv2, phases
d = phases.design()
def f(a):
    v, m = a
    r = hv2.calibrate(f"dev_v{round(v*1000):04d}_m{round(m*100):03d}", v, m, None, design=d)
    return {k: r[k] for k in ("key", "vhat", "mu_hat", "k", "levels", "race", "flag", "err_mV", "mu_err_rel")}
with Pool(2) as p:
    for r in p.map(f, [(0.80, 0.55), (0.95, 0.90)]):
        print(json.dumps(r, default=float), flush=True)
