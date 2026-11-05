"""Calibrated scheme-A race surrogate (DECISIONS.md W4). Parameters: summary/surrogate_params.json (calib_fit.py).

Per class k (classes 0..4 here), with bank factors g1, g2 (1 on a nominal die):
  rail at C2 start   V_k = R_k + dR_k + alpha * sum_i F[i,k] g1[i,k] (WMIN + x_i T1) + c0
  C2 slope           s_k = gamma * sum_i F[i,k] g2[i,k]
  trip (from C2)     t_k = (Theta_k + dTheta_k - V_k) / s_k          (Theta_k is the effective trip level: it includes
                                                                    the comparator/latch delay at the average C2 slope)
  time differences (gaps, margins) are scaled by gap_factor = s_bar/s_g (local slope at the trip vs the average slope)
  trip during C1  <=> V_k >= Theta_k + dTheta_k for any k  -> the sample fails (strict reading)
  correct         <=> argmin_k t_k = label, runner-up gap t_(2) - t_(1) >= G_res, no trip during C1.
Mismatch (W5): size-scaled V_th only. Bank (i,k) has sigma = anchor*sqrt(780/(540*F[i,k])); its DVTH sets g1, g2 through
the device-model curves of bank_dc.py. Per-class chain devices move Theta_k (coefficients from the W4.3 SPICE
sensitivity runs) and the reset switch moves R_k."""
import json
import numpy as np
import wcommon as W

PFILE = W.SUMM / "surrogate_params.json"
_P = None


def params():
    global _P
    if _P is None:
        _P = json.loads(PFILE.read_text())
    return _P


def reload():
    global _P
    _P = None
    return params()


# ----------------------------------------------------------------------------- bank factor curves
_BANK = None


def bank_curves():
    global _BANK
    if _BANK is None:
        b = json.loads((W.SUMM / "bank_dc.json").read_text())["0.65"]
        dv = np.array(b["dvth"])
        _BANK = (dv, np.array(b["data"]["g1"]["1.3"]["30"]["factor"]), np.array(b["data"]["g2"]["1.3"]["30"]["factor"]))
    return _BANK


def g_of(d, which):
    dv, f1, f2 = bank_curves()
    return np.interp(np.clip(d, dv[0], dv[-1]), dv, f1 if which == 1 else f2)


# ----------------------------------------------------------------------------- dies
class Dies:
    """Analytic Monte Carlo dies: one z-score per bank position, per class-chain device and per reset switch.
    anchors: array (n,) of anchor sigmas [V] (one per die). Common random numbers across weight sets."""

    def __init__(self, n, anchors, seed):
        rng = np.random.default_rng(seed)
        self.n = n
        self.anchor = np.broadcast_to(np.asarray(anchors, float), (n,)).copy()
        self.z_bank = rng.standard_normal((n, 6, 5))
        p = params()
        self.chain = list(p["chain"].keys())
        self.z_chain = rng.standard_normal((n, 5, len(self.chain)))
        self.z_reset = rng.standard_normal((n, 5))

    def offsets(self):
        """dR (n,5), dTheta (n,5) in volts."""
        p = params()
        a = self.anchor[:, None]
        sR = a * np.sqrt(780.0 / p["reset"]["area"])
        dR = p["reset"]["coef"] * self.z_reset * sR
        dT = np.zeros((self.n, 5))
        for j, nm in enumerate(self.chain):
            c = p["chain"][nm]
            dT += c["coef"] * self.z_chain[:, :, j] * a * np.sqrt(780.0 / c["area"])
        return dR, dT

    def bank_factors(self, F):
        F = np.asarray(F, float)
        sig = self.anchor[:, None, None] * np.sqrt(780.0 / (540.0 * np.maximum(F, 1.0)))[None]
        d = self.z_bank * sig
        return g_of(d, 1), g_of(d, 2)


def make_dies(n_per_anchor, anchors_mV, seed):
    an = np.concatenate([np.full(n_per_anchor, a / 1000.0) for a in anchors_mV])
    return Dies(len(an), an, seed)


# ----------------------------------------------------------------------------- race
def corner_params(vth=0.65, timing=None):
    """Parameter set for a corner (re-trimmed |V_th|) and host timing."""
    p = params()
    key = f"{vth:.2f}"
    base = p["corners"][key] if key in p.get("corners", {}) else p["corners"]["0.65"]
    q = dict(base)
    tm = dict(W.TIMING0, **(timing or {}))
    q.update(T1=tm["T1"], WMIN=tm["WMIN"], V2off=tm["V2off"])
    if tm["V2off"] != 0.25:
        q["gamma"] = q["gamma"] * p["v2off_gamma_scale"][f"{tm['V2off']:.2f}"]
    if timing is not None and "timing_overrides" in p:
        q.update(p["timing_overrides"].get(timing_key(tm), {}))
    return q


def timing_key(tm):
    return f"T{tm['T1']:g}_W{tm['WMIN']:g}_V2o{tm['V2off']:g}"


def race(F, X, q, dies=None):
    """Trip times from C2 start t (D,N,5) [us] and the C1-trip flag (D,N). D = 1 for the nominal die."""
    F = np.asarray(F, float); X = np.asarray(X, float)
    if dies is None:
        g1 = np.ones((1, 6, 5)); g2 = g1; dR = np.zeros((1, 5)); dT = np.zeros((1, 5))
    else:
        g1, g2 = dies.bank_factors(F)
        dR, dT = dies.offsets()
    Fe1 = F[None] * g1                                                   # (D,6,5)
    drive = q["T1"] * np.einsum("ni,dik->dnk", X, Fe1) + q["WMIN"] * Fe1.sum(1)[:, None, :]
    V = (np.asarray(q["R"])[None, None, :] + dR[:, None, :] + q["alpha"] * drive + q["c0"])
    thr = np.asarray(q["Theta"])[None, None, :] + dT[:, None, :]
    s = q["gamma"] * (F[None] * g2).sum(1)                               # (D,5) V/us
    t = (thr - V) / s[:, None, :]
    c1 = (V >= thr).any(2)
    return t, c1


def margin(F, X, y, q, dies=None):
    """M = gap_factor * min_{j != y}(t_j - t_y) - G_res (D,N); -1e6 where a class trips during C1."""
    t, c1 = race(F, X, q, dies)
    t = t * q.get("gap_factor", 1.0)
    N = len(y)
    ty = t[:, np.arange(N), y]
    tt = t.copy(); tt[:, np.arange(N), y] = np.inf
    M = tt.min(2) - ty - q["G_res"]
    return np.where(c1, -1e6, M)


def accuracy(F, X, y, q, dies=None):
    return (margin(F, X, y, q, dies) >= 0).mean(1)                      # per die


def predict(F, X, q, dies=None):
    """winner (D,N), gap (D,N), runner-up (D,N), c1 (D,N)."""
    t, c1 = race(F, X, q, dies)
    t = t * q.get("gap_factor", 1.0)
    o = np.argsort(t, 2)
    w, r = o[..., 0], o[..., 1]
    gap = np.take_along_axis(t, r[..., None], 2)[..., 0] - np.take_along_axis(t, w[..., None], 2)[..., 0]
    return w, gap, r, c1


def req_nominal(X, y, q, m_us):
    """Score-margin requirement (finger units) for the nominal-die MILP: gf (t_j - t_y) >= G_res + m  <=>
    x.(F_y - F_j) >= [s (G_res + m)/gf - (Theta_j - Theta_y) + (R_j - R_y)] / (alpha T1), with s = 60 gamma."""
    s = 60 * q["gamma"] / q.get("gap_factor", 1.0)
    R, Th = np.asarray(q["R"]), np.asarray(q["Theta"])
    req = np.zeros((len(y), 5))
    for j in range(5):
        req[:, j] = (s * (q["G_res"] + m_us) - (Th[j] - Th[y]) + (R[j] - R[y])) / (q["alpha"] * q["T1"])
    return req
