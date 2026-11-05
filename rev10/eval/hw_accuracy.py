"""Hardware accuracy estimate for the T10 design iteration on the wound test set.
Race model calibrated on SPICE (lab corner, |Vth| 0.85 V, warm start):
  t_k = K * (1 + delta_k / SWING) / s_k,  K = 1.03e5 us*um,  SWING = 1.1 V,  s_k = 10 um * sum_i x_i F_ik * g_ik
Correct = true class trips first AND runner-up trails by more than the lock latency."""
import numpy as np
REPO = "/home/claude/w/repo/data/"
d = np.load(REPO + "trace2_data.npz"); X, y = d["X_test"], d["y_test"]
F = np.load(REPO + "trace2_fingers_retrained.npy").astype(float)          # 6 x 5, 60 per column
K, SWING, VOV = 1.03e5, 1.1, 0.83
def evaluate(t_lock, sig_f=0.0, sig_c=0.0, n_die=1, seed=1):
    rng = np.random.default_rng(seed); acc = []; detail = None
    for _ in range(n_die):
        # per-finger Vth offsets -> per-bank current factor (mean over its fingers)
        g = np.ones_like(F)
        if sig_f > 0:
            for i in range(6):
                for k in range(5):
                    n = int(F[i, k])
                    if n: g[i, k] = np.mean(((VOV - rng.normal(0, sig_f, n)) / VOV) ** 2)
        delta = rng.normal(0, sig_c, 5) if sig_c > 0 else np.zeros(5)
        s = 10.0 * X @ (F * g)                                              # um, per sample x class
        t = K * (1 + delta / SWING) / np.maximum(s, 1e-9)
        o = np.argsort(t, axis=1); first, second = o[:, 0], o[:, 1]
        gap = t[np.arange(len(y)), second] - t[np.arange(len(y)), first]
        ok = (first == y) & (gap > t_lock)
        acc.append(ok.mean())
        if detail is None: detail = dict(first=first, gap=gap, tfirst=t[np.arange(len(y)), first], ok=ok)
    return np.array(acc), detail
s0 = 10.0 * X @ F
sw = (np.argmax(s0, 1) == y).mean()
print(f"software (integer fingers, argmax): {sw*100:.2f}%  ({int(round(sw*90))}/90)")
for tl in (0, 18, 21, 25):
    a, det = evaluate(tl)
    print(f"hardware nominal, lock latency {tl:2d} us: {a[0]*100:.2f}%   race to first trip {det['tfirst'].min():.0f}-{det['tfirst'].max():.0f} us")
a, det = evaluate(21)
right = (det["first"] == y)
print(f"  of the software-correct samples, lost to the lock latency: {int(np.sum(right & ~det['ok']))}; winner/runner-up gap among correct: min {det['gap'][right].min():.1f} us, median {np.median(det['gap'][right]):.0f} us")
for sf, sc in ((0.020, 0.020), (0.050, 0.050), (0.050, 0.0), (0.0, 0.050)):
    a, _ = evaluate(21, sf, sc, n_die=1000)
    print(f"Monte Carlo 1000 dies, finger sigma {sf*1e3:.0f} mV, comparator sigma {sc*1e3:.0f} mV: mean {a.mean()*100:.1f}%, 5th pct {np.percentile(a,5)*100:.1f}%, worst {a.min()*100:.1f}%")

print("\n--- host duty-cycle scaling by 1/m (race and all gaps stretch by m), lock latency 21 us ---")
for m in (1, 2, 4, 8):
    K = 1.03e5 * m
    a0, det = evaluate(21)
    a20, _ = evaluate(21, 0.020, 0.020, n_die=500)
    a50, _ = evaluate(21, 0.050, 0.050, n_die=500)
    print(f"m={m}: race {det['tfirst'].min()/1e3:.2f}-{det['tfirst'].max()/1e3:.2f} ms | nominal {a0[0]*100:5.1f}% | "
          f"sigma 20 mV mean {a20.mean()*100:5.1f}% (5th pct {np.percentile(a20,5)*100:.1f}%) | "
          f"sigma 50 mV mean {a50.mean()*100:5.1f}% (5th pct {np.percentile(a50,5)*100:.1f}%)")
