"""Scheme A (integrate, then race) race model with mismatch.
C1: row i at V1=1.62 V for x_i*T1 (one window). C2: all rows at V2, equal-width columns ramp together.
Rail units: full column at V1 traverses SWING in TAU_FULL. Trip when rail reaches SWING + delta_k."""
import numpy as np
REPO = "/home/claude/w/repo/data/"
d = np.load(REPO + "trace2_data.npz"); Xtr, ytr, Xte, yte = d["X_train"], d["y_train"], d["X_test"], d["y_test"]
F0 = np.load(REPO + "trace2_fingers_retrained.npy").astype(int)
F1 = np.load("/home/claude/w/eval/F_hw_m4_firstpass.npy").astype(int)
SWING, TAU_FULL, VTH = 1.1, 187.0, 0.85
RESET_AREA = 8000.0   # M75-79 400/20
def die(n, sig_anchor, seed):
    rng = np.random.default_rng(seed)
    sf = sig_anchor * np.sqrt(780 / 540)                                   # finger 10x54 um
    dv = rng.normal(0, sf, (n, 6, 5, 60)); dv[0] = 0
    a = lambda A: sig_anchor * np.sqrt(780 / A)
    sc = np.sqrt(a(7020)**2 + (a(2000)/3)**2 + (0.18*a(400))**2 + a(RESET_AREA)**2)   # variant C comparator + rail reset level
    dl = rng.normal(0, sc, (n, 5)); dl[0] = 0
    return dv, dl
SSW = 2 * 0.080 / np.log(10)
def sp(x): return SSW * np.logaddexp(0, x / SSW)
def bank(F, dv, vov):
    f = (sp(vov - dv) / sp(vov)) ** 2
    cs = np.concatenate([np.zeros(dv.shape[:3] + (1,)), np.cumsum(f, 3)], 3)
    return np.take_along_axis(cs, F[None, :, :, None].repeat(dv.shape[0], 0), 3)[..., 0]  # summed factor per bank
WMIN, THR_MARGIN = 20.0, 0.05
def trips(F, X, dv, dl, T1, V2):
    vov1, vov2 = 1.68 - VTH, 3.3 - V2 - VTH
    r = SWING / TAU_FULL / 60.0                                            # V/us per finger-equivalent at V1
    B1 = bank(F, dv, vov1); B2 = bank(F, dv, vov2) * (sp(vov2) / sp(vov1)) ** 2      # die x 6 x 5
    N = len(X); nd = dv.shape[0]; t = np.full((nd, N, 5), np.inf)
    for n in range(N):
        on = WMIN + X[n] * T1; order = np.argsort(on); ends = np.concatenate([[0.0], on[order]])
        V = np.zeros((nd, 5)); thr = SWING - THR_MARGIN + dl; alive = np.ones(6, bool); tprev = 0.0
        tk = np.full((nd, 5), np.inf)
        for j, i in enumerate(order):                                       # C1 segments
            rate = r * np.einsum("i,dik->dk", alive.astype(float), B1)
            dt = on[i] - tprev
            hit = (V + rate * dt >= thr) & np.isinf(tk)
            tk[hit] = (tprev + (thr - V) / np.maximum(rate, 1e-12))[hit]
            V = V + rate * dt; tprev = on[i]; alive[i] = False
        rate = r * np.einsum("i,dik->dk", alive.astype(float), B1); V = V + rate * (WMIN + T1 - tprev)
        s2 = r * B2.sum(1)                                                  # C2: all rows on
        c2 = WMIN + T1 + 5.0 + np.maximum(thr - V, 0) / s2
        tk = np.where(np.isinf(tk), c2, tk); t[:, n, :] = tk
    return t
def acc(F, X, y, dv, dl, T1, V2, t_lock=14.0):
    t = trips(F, X, dv, dl, T1, V2); N = len(y)
    ty = t[:, np.arange(N), y]; tt = t.copy(); tt[:, np.arange(N), y] = np.inf
    return ((tt.min(2) - ty) > t_lock).mean(1), t
if __name__ == "__main__":
    for name, F in (("hw-trained", F1), ("original", F0)):
        smax = (Xtr @ F).max()                                              # fingers*x, train set
        T1 = 0.9 * TAU_FULL * 60 / smax
        dv, dl = die(300, 0.050, 3)
        print(f"{name}: max train score {smax:.1f} finger-units -> T1 = {T1:.0f} us")
        for V2 in (1.62, 1.8, 1.95, 2.1):
            a, t = acc(F, Xte, yte, dv, dl, T1, V2)
            ty = t[0, np.arange(len(yte)), yte]
            print(f"   V2={V2:.2f}: nominal {a[0]*100:5.1f}% | sigma50 mean {a[1:].mean()*100:5.1f}% worst5% {np.percentile(a[1:],5)*100:5.1f}% | race {np.nanmin(ty):.0f}-{np.nanmax(ty[np.isfinite(ty)]):.0f} us")
