"""Study 3 training and selection (DECISIONS S3.2-S3.3). TRAINING SAMPLES ONLY: this file never reads X_test/y_test.
The weight-retraining study's family (a) (margin-maximising on the nominal race surrogate, results/weights_schemeA/scripts) extended to
the bias row of R10.2-bias.

Surrogate (weight-retraining study W4 form, bias row added, v2.1 parameters after S3.2 recalibration):
  rail at C2 start  V_k = R_k + alpha * sum_i F[i,k] g1 (WMIN + x_i T1) + alpha_b * Fb[k] g1b (WMIN + XB T1) + c0
  C2 slope          s_k = gamma * sum_i F[i,k] g2            (the bias row is off in C2)
  trip from C2      t_k = gap_factor * (Theta_k + dTheta_k - V_k) / s_k ; a trip during C1 (V_k >= Theta_k) fails
  correct           argmin t = label and runner-up gap >= G_res (+ m in training)
Mismatch dies: the weight-retraining study's analytic dies (size-scaled V_th, anchors 20/35 mV) for the 6 x 5 banks and the class-chain
devices; bias banks get their own z-scores (seed + 500000). The reset-switch term is OFF under v2.1 mode G (S3.2: the
rails start below the reset floor after the 1 s-off power-up, so the reset switches do not set R_k).

Usage: python3 s3_train.py probe                 the S3.2 probe matrix (weight-retraining study nominal parameters, alpha_b = alpha)
       python3 s3_train.py cv [nproc]            CV of every config on the 20 group splits of T -> summary/S3_jobs/
       python3 s3_train.py select                CV table + finalists -> summary/s3_cv.json; trains finalists on T
       python3 s3_train.py check                 tooling check: with Fb = 0 and the weight-retraining study's parameters this surrogate
                                                 reproduces surrogate.py on T for the old weights and cand_a"""
import json, os, pathlib, sys, time
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
sys.dont_write_bytecode = True
import numpy as np

WU = pathlib.Path(__file__).resolve().parents[1]
REPO = WU.parents[1]
WSS = REPO / "results/weights_schemeA"
sys.path.insert(0, str(WSS / "scripts"))
import wcommon as W          # noqa: E402  (read-only; XTR/YTR used, XTE/YTE never)
import optim as O            # noqa: E402
import surrogate as SG       # noqa: E402

SPL = json.loads((WSS / "summary/splits.json").read_text())
T = np.array(SPL["T"]); S = np.array(SPL["S"]); K = np.array(SPL["K"])
XB = 0.5
FBMAX = 30
NNZ_IN = (15, 21)
JOBS = WU / "summary/S3_jobs"
PFILE = WU / "summary/s3_surrogate_params.json"
WDIR = WU / "weights"
MODES = {"eq60": (60, 60), "le60": (50, 60)}
MS = (10, 20, 30, 45)
BUDGETS = ("b134", "b138")       # b134: input + bias banks <= 21 (134 TFTs at most); b138: input <= 21, bias <= 4
CONFIGS = [(md, m, bud) for md in MODES for m in MS for bud in BUDGETS]


def cfg_name(c):
    return f"{c[0]}_m{c[1]}_{c[2]}"


# ----------------------------------------------------------------------------- parameters
def params(stage="recal"):
    """Nominal surrogate parameters. stage 'retrain_study': the weight-retraining study's v1-calibrated nominal set, alpha_b = alpha (used only
    for the S3.2 probe); 'recal': the S3.2 v2.1 recalibration (summary/s3_surrogate_params.json)."""
    if stage == "retrain_study":
        q = dict(SG.params()["corners"]["0.65"])
        q["alpha_b"] = q["alpha"]
    else:
        q = dict(json.loads(PFILE.read_text())["nominal"])
    q.update(XB=XB)
    q["R"] = np.asarray(q["R"], float); q["Theta"] = np.asarray(q["Theta"], float)
    return q


class BiasDies(SG.Dies):
    def __init__(self, n, anchors, seed):
        super().__init__(n, anchors, seed)
        self.z_bias = np.random.default_rng(seed + 500000).standard_normal((n, 5))

    def bias_factors(self, Fb):
        sig = self.anchor[:, None] * np.sqrt(780.0 / (540.0 * np.maximum(np.asarray(Fb, float), 1.0)))[None]
        d = self.z_bias * sig
        return SG.g_of(d, 1)


def eval_dies(seed=41000, n=250):
    return BiasDies(2 * n, np.concatenate([np.full(n, 0.020), np.full(n, 0.035)]), seed)


def race(F6, Fb, X, q, dies=None, reset_term=False):
    """t (D,N,5) (gap-scaled, us from C2 start) and C1-trip flag (D,N)."""
    F6 = np.asarray(F6, float); Fb = np.asarray(Fb, float); X = np.asarray(X, float)
    if dies is None:
        g1 = np.ones((1, 6, 5)); g2 = g1; gb = np.ones((1, 5)); dR = np.zeros((1, 5)); dT = np.zeros((1, 5))
    else:
        g1, g2 = dies.bank_factors(F6)
        gb = dies.bias_factors(Fb)
        dR, dT = dies.offsets()
        if not reset_term:
            dR = np.zeros_like(dR)
    Fe1 = F6[None] * g1
    drive = q["T1"] * np.einsum("ni,dik->dnk", X, Fe1) + q["WMIN"] * Fe1.sum(1)[:, None, :]
    bias = (Fb[None] * gb) * (q["WMIN"] + q["XB"] * q["T1"])
    V = q["R"][None, None] + dR[:, None] + q["alpha"] * drive + q["alpha_b"] * bias[:, None, :] + q["c0"]
    thr = q["Theta"][None, None] + dT[:, None]
    s = q["gamma"] * (F6[None] * g2).sum(1)
    t = q.get("gap_factor", 1.0) * (thr - V) / s[:, None, :]
    return t, (V >= thr).any(2)


def margins(F6, Fb, X, y, q, dies=None, reset_term=False):
    t, c1 = race(F6, Fb, X, q, dies, reset_term)
    N = len(y)
    ty = t[:, np.arange(N), y]
    tt = t.copy(); tt[:, np.arange(N), y] = np.inf
    M = tt.min(2) - ty - q["G_res"]
    return np.where(c1, -1e6, M)


def accuracy(F6, Fb, X, y, q, dies=None, reset_term=False):
    return (margins(F6, Fb, X, y, q, dies, reset_term) >= 0).mean(1)


# ----------------------------------------------------------------------------- feasibility and starts
def feasible(F6, Fb, mode, bud):
    F6 = np.asarray(F6); Fb = np.asarray(Fb)
    lo, hi = MODES[mode]
    nin, nb = int((F6 > 0).sum()), int((Fb > 0).sum())
    ok = (F6 >= 0).all() and (F6.sum(0) >= lo).all() and (F6.sum(0) <= hi).all() and NNZ_IN[0] <= nin <= NNZ_IN[1]
    ok = ok and (Fb >= 0).all() and (Fb <= FBMAX).all()
    return bool(ok and ((nin + nb <= 21) if bud == "b134" else (nb <= 4)))


def lr_start(X, y, lam, bud):
    Wt, b = O.fit_lr(X, y, lam, True, True)
    F6 = O.to_fingers(Wt)
    Wc = Wt - Wt.mean(1, keepdims=True) - Wt.mean(0, keepdims=True) + Wt.mean()
    P = Wc - Wc.min(1, keepdims=True)
    c = 60.0 / P.sum(0)[0]
    Fb = np.clip(np.rint(c * (b - b.min()) / (20.0 / 170.0 + XB)).astype(int), 0, FBMAX)
    if bud == "b134":                      # make room: drop the smallest input banks until input + bias banks <= 21
        while (F6 > 0).sum() + (Fb > 0).sum() > 21 and (F6 > 0).sum() > NNZ_IN[0]:
            i, k = np.unravel_index(np.argmin(np.where(F6 > 0, F6, 10 ** 6)), F6.shape)
            v = F6[i, k]; F6[i, k] = 0; F6[np.argmax(F6[:, k]), k] += v
        while (F6 > 0).sum() + (Fb > 0).sum() > 21:
            k = int(np.argmin(np.where(Fb > 0, Fb, 10 ** 6))); Fb[k] = 0
    else:
        while (Fb > 0).sum() > 4:
            Fb = Fb - Fb[Fb > 0].min(); Fb = np.maximum(Fb, 0)
    return F6, Fb


# ----------------------------------------------------------------------------- objective and descent
def objective(F6, Fb, X, y, q, m, tie=1e-3):
    M = margins(F6, Fb, X, y, q)[0]
    v = (M - m >= 0).mean()
    return v + tie * np.where(M <= -1e5, 0.0, 1 / (1 + np.exp(-np.clip((M - m) / 5.0, -60, 60)))).mean()


def moves(F6, Fb, mode, bud):
    lo, hi = MODES[mode]
    for k in range(5):
        for a in range(6):
            for b in range(6):
                if a != b:
                    for d in (1, 2, 3):
                        if F6[a, k] >= d:
                            G = F6.copy(); G[a, k] -= d; G[b, k] += d
                            yield G, Fb
            if lo < hi:
                for d in (1, 2, 3):
                    for s in (-1, 1):
                        G = F6.copy(); G[a, k] += s * d
                        if G[a, k] >= 0:
                            yield G, Fb
        for d in (1, 2, 3):
            for s in (-1, 1):
                H = Fb.copy(); H[k] += s * d
                yield F6, H


def descend(F6, Fb, X, y, q, m, mode, bud, max_iter=2000):
    F6 = np.array(F6, int); Fb = np.array(Fb, int)
    assert feasible(F6, Fb, mode, bud), (F6, Fb)
    best = objective(F6, Fb, X, y, q, m)
    for _ in range(max_iter):
        cand = None
        for G, H in moves(F6, Fb, mode, bud):
            if not feasible(G, H, mode, bud):
                continue
            v = objective(G, H, X, y, q, m)
            if v > best + 1e-12 and (cand is None or v > cand[0]):
                cand = (v, G, H)
        if cand is None:
            break
        best, F6, Fb = cand
    return F6, Fb, best


def train(X, y, q, cfg):
    mode, m, bud = cfg
    best, tried = None, []
    for lam in (1e-4, 1e-3, 1e-2):
        F6, Fb = lr_start(X, y, lam, bud)
        if not feasible(F6, Fb, mode, bud):            # LR start has column sums 60: feasible in both modes
            continue
        F6, Fb, v = descend(F6, Fb, X, y, q, m, mode, bud)
        tried.append(dict(start=f"lr{lam:g}", value=float(v)))
        if best is None or v > best[0] + 1e-12:
            best = (v, F6, Fb, f"lr{lam:g}")
    return best[1], best[2], dict(tried=tried, chosen=best[3], train_objective=float(best[0]))


def score(F6, Fb, X, y, q, dies):
    a_nom = float(accuracy(F6, Fb, X, y, q)[0])
    a_mm = float(accuracy(F6, Fb, X, y, q, dies).mean())
    return dict(A_nom=a_nom, A_mm=a_mm, S3=0.5 * a_nom + 0.5 * a_mm)


_DIES = None


def job(args):
    cfg, k = args
    out = JOBS / f"{cfg_name(cfg)}_{k:02d}.json"
    if out.exists():
        return json.loads(out.read_text())
    global _DIES
    if _DIES is None:
        _DIES = eval_dies()
    sp = SPL["cv_T"][k]
    tr, va = np.array(sp["train"]), np.array(sp["val"])
    q = params()
    t0 = time.time()
    F6, Fb, info = train(W.XTR[tr], W.YTR[tr], q, cfg)
    sc = score(F6, Fb, W.XTR[va], W.YTR[va], q, _DIES)
    r = dict(config=cfg_name(cfg), split=k, F6=F6.tolist(), Fb=Fb.tolist(), banks_in=int((F6 > 0).sum()), banks_bias=int((Fb > 0).sum()),
             n_tft=113 + int((F6 > 0).sum()) + int((Fb > 0).sum()), colsums=F6.sum(0).tolist(), info=info, **sc,
             wall_s=round(time.time() - t0, 1))
    out.write_text(json.dumps(r, indent=1, default=float))
    return r


def train_final(cfg, stage="recal", name=None):
    q = params(stage)
    F6, Fb, info = train(W.XTR[T], W.YTR[T], q, cfg)
    WDIR.mkdir(exist_ok=True)
    name = name or f"S3_{cfg_name(cfg)}"
    np.savez(WDIR / f"{name}.npz", F6=F6, Fb=Fb)
    rec = dict(name=name, config=cfg_name(cfg), stage=stage, F6=F6.tolist(), Fb=Fb.tolist(), colsums=F6.sum(0).tolist(),
               banks_in=int((F6 > 0).sum()), banks_bias=int((Fb > 0).sum()), n_tft=113 + int((F6 > 0).sum()) + int((Fb > 0).sum()),
               train_accuracy_T=float(accuracy(F6, Fb, W.XTR[T], W.YTR[T], q)[0]), info=info)
    (WDIR / f"{name}.json").write_text(json.dumps(rec, indent=1, default=float))
    return rec


def check():
    """Fb = 0 and weight-retraining study parameters -> identical margins to surrogate.py (nominal and on 10 dies, reset term on)."""
    q = params("retrain_study")
    qa = SG.corner_params(0.65)
    dies_a = SG.make_dies(5, (20, 35), 41000)
    dies_b = BiasDies(10, dies_a.anchor, 41000)
    out = {}
    for nm, F in (("old", W.F_OLD), ("cand_a", np.load(WSS / "weights/cand_a.npy"))):
        Ma = SG.margin(F, W.XTR[T], W.YTR[T], qa, None); Mb = margins(F, np.zeros(5), W.XTR[T], W.YTR[T], q)
        Md_a = SG.margin(F, W.XTR[T], W.YTR[T], qa, dies_a); Md_b = margins(F, np.zeros(5), W.XTR[T], W.YTR[T], q, dies_b, reset_term=True)
        out[nm] = dict(max_abs_diff_nominal_us=float(np.max(np.abs(Ma - Mb))), max_abs_diff_dies_us=float(np.max(np.abs(Md_a - Md_b))))
    (WU / "summary/s3_check.json").write_text(json.dumps(out, indent=1))
    print(out)


if __name__ == "__main__":
    w = sys.argv[1]
    if w == "check":
        check()
    elif w == "probe":
        print(json.dumps({k: v for k, v in train_final(("le60", 30, "b138"), "retrain_study", "S3_probe").items() if k != "info"}, indent=1))
    elif w == "cv":
        from multiprocessing import Pool
        JOBS.mkdir(parents=True, exist_ok=True)
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        jobs = [(c, k) for c in CONFIGS for k in range(len(SPL["cv_T"]))]
        t0 = time.time()
        with Pool(n) as p:
            for i, r in enumerate(p.imap_unordered(job, jobs), 1):
                print(f"[{i}/{len(jobs)} {time.time()-t0:6.0f}s] {r['config']} split {r['split']} S3 {r['S3']:.3f} nom {r['A_nom']:.3f} "
                      f"Fb {r['Fb']} tft {r['n_tft']} wall {r['wall_s']}", flush=True)
