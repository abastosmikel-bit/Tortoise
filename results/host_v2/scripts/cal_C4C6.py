"""Run the C4 and C6 calibration sessions ahead of their classifications (cached; phases.py reuses them)."""
import phases as P
for d in P.C4_DIES:
    c = P.cal(0.65, 1.0, d); print(c['key'], c.get('err_mV'), c.get('mu_hat'), c.get('k'), c.get('flag'), flush=True)
for v in P.C6_VTH:
    c = P.cal(v, 1.0); print(c['key'], c.get('err_mV'), c.get('mu_hat'), c.get('k'), c.get('flag'), flush=True)
