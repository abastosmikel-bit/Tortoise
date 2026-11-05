"""Exact duty-cycle staircase: rows pulse in phase at each period start for x_i*P/m.
Rail 'charge' S_k(t) = sum_i 10*F_ik * A_i(t) (um*us); trip when S_k = K. Compare with average model t = K*m/s."""
import numpy as np
d = np.load("/home/claude/w/repo/data/trace2_data.npz"); X, y = d["X_test"], d["y_test"]
def trip_times(x, F, K, m=4, P=40.0):
    on = x / m * P                                    # per-row on time per period
    s_full = 10 * (F.T @ np.ones(6))                  # not used
    t = np.zeros(5)
    for k in range(5):
        w = 10 * F[:, k]; per = (w * on).sum()        # charge per full period
        n = int(np.floor(K / per)); rem = K - n * per # full periods, then remainder inside the last period
        # inside a period, rows are on from 0 to on_i: charge rate piecewise constant, decreasing
        order = np.argsort(on); tt = 0.0; acc = 0.0; ends = np.concatenate([[0], np.sort(on)])
        rate = w.sum() if True else 0
        active = np.ones(6, bool); tcur = 0.0; left = rem
        for j in order:
            r = (w * active).sum(); dt = on[j] - tcur
            if r * dt >= left: tcur += left / r; left = 0; break
            left -= r * dt; tcur = on[j]; active[j] = False
        t[k] = n * P + tcur
    return t
def gaps(F, K, m=4, P=40.0, idx=None):
    out = []
    for i in (range(len(y)) if idx is None else idx):
        tk = trip_times(X[i], F, K, m, P); ty = tk[y[i]]; tt = tk.copy(); tt[y[i]] = np.inf
        out.append((tt.min() - ty, tt.argmin()))
    return out
if __name__ == "__main__":
    F0 = np.load("/home/claude/w/repo/data/trace2_fingers_retrained.npy").astype(float)
    F1 = np.load("F_hw_m4_firstpass.npy").astype(float)
    cases = [("#46 orig", F0, 1.03e5, 46, 28.4), ("#17 orig", F0, 1.03e5, 17, 18.0), ("#31 orig", F0, 1.03e5, 31, -0.3),
             ("#31 final", F1, 1.03e5 * 1.09, 31, -3.2)]
    for name, F, K, i, spice in cases:
        s = 10 * X[i] @ F; ta = K * 4 / s; ty = ta[y[i]]; tt = ta.copy(); tt[y[i]] = np.inf
        g_st, r = gaps(F, K, idx=[i])[0]
        print(f"{name:10s}: average model gap {tt.min()-ty:+6.1f} us | staircase gap {g_st:+6.1f} us | SPICE {spice:+6.1f} us")
