"""Hardware-aware integer retraining of the crossbar finger matrix.
Model (SPICE-validated, lab corner |Vth| 0.85 V): t_k = K*m*(1 + delta_k/SWING) / s_k, s_k = 10 um * sum_i x_i F_ik g_ik.
Sample correct iff margin = min_{k!=y}(t_k - t_y) - T_LOCK > 0 and t_y < T_WIN."""
import numpy as np, sys, time, json
REPO = "/home/claude/w/repo/data/"
d = np.load(REPO + "trace2_data.npz")
Xtr, ytr, Xte, yte = d["X_train"], d["y_train"], d["X_test"], d["y_test"]
F0 = np.load(REPO + "trace2_fingers_retrained.npy").astype(int)
K, SWING, VOV, T_LOCK, T_WIN = 1.03e5, 1.1, 0.83, 21.0, 2500.0

def dies(n, sig, seed):
    """Per-finger current factors (cumsum table for fast bank means) and comparator offsets. Die 0 = nominal."""
    rng = np.random.default_rng(seed)
    fac = ((VOV - rng.normal(0, sig, (n, 6, 5, 60))) / VOV) ** 2
    fac[0] = 1.0
    cs = np.concatenate([np.zeros((n, 6, 5, 1)), np.cumsum(fac, axis=3)], axis=3)
    dl = rng.normal(0, sig, (n, 5)); dl[0] = 0
    return cs, dl
def margins(F, X, y, cs, dl, m):
    n = cs.shape[0]
    Fi = F[None, :, :, None].repeat(n, 0)
    g = np.take_along_axis(cs, Fi, axis=3)[..., 0] / np.maximum(F, 1)          # die x 6 x 5
    s = 10.0 * np.einsum("ni,dik->dnk", X, F * g)                                # die x N x 5
    t = K * m * (1 + dl[:, None, :] / SWING) / np.maximum(s, 1e-6)
    N = len(y); ty = t[:, np.arange(N), y]
    tt = t.copy(); tt[:, np.arange(N), y] = np.inf
    mg = tt.min(axis=2) - ty - T_LOCK
    return np.minimum(mg, T_WIN - ty)                                            # die x N
def objective(F, cs, dl, m, tau=4.0):
    mg = margins(F, Xtr, ytr, cs, dl, m)
    return (1 / (1 + np.exp(-np.clip(mg / tau, -50, 50)))).mean()
def accuracy(F, X, y, cs, dl, m):
    return (margins(F, X, y, cs, dl, m) > 0).mean(axis=1)                        # per die
def moves(F):
    for k in range(5):
        for a in range(6):
            if F[a, k] == 0: continue
            for b in range(6):
                if a != b:
                    G = F.copy(); G[a, k] -= 1; G[b, k] += 1; yield G
def climb(F, cs, dl, m, t_budget):
    best = objective(F, cs, dl, m); t0 = time.time()
    while time.time() - t0 < t_budget:
        cand = max(((objective(G, cs, dl, m), G) for G in moves(F)), key=lambda z: z[0])
        if cand[0] <= best + 1e-9: break
        best, F = cand
    return F, best
if __name__ == "__main__":
    m = float(sys.argv[1]) if len(sys.argv) > 1 else 4
    budget = float(sys.argv[2]) if len(sys.argv) > 2 else 200
    cs, dl = dies(33, 0.050, 7)
    start = np.load(sys.argv[3]).astype(int) if len(sys.argv) > 3 else F0
    F, obj = climb(start, cs, dl, m, budget)
    assert (F.sum(0) == 60).all() and (F >= 0).all()
    np.save(f"F_hw_m{int(m)}.npy", F)
    print(f"m={m:g}  train objective {objective(start, cs, dl, m):.3f} -> {obj:.3f}")
    print(F)
