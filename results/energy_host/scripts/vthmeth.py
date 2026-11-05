"""V_th-learning measurements (B3). Each returns the host's raw estimate (before the design-time offset correction).

 (b)  replica: one extra TFT on its own 3 pads (Variant 3R; not connected to the classifier). Host: source pad 3.3 V,
      drain pad 0 V through a current meter, gate pad at V_SG = REP_VSG (3 points); 3-point square-law extraction with a
      series-resistance term: sqrt(I) = a*(V_SG - |V_th| - I*R), solved exactly for (a, |V_th|, R). DC (.op per point).
 (a1) supply current: host-only, needs a current meter on the host's VDD supply (no die change). rstr held low (rails
      clamped by the reset switches, latches held in reset), phib low during reset as in the protocol and high from
      290 us (dummy columns isolated during the ramp), normal rstb; rows
      ramped 3.3 -> 1.3 V over 4 ms after a 300 us reset. dI_DD(V_row) = I_DD - I_DD(rows 3.3 V). The same 3-point
      extraction at the V_SG where dI = SUP_I1 * (1, 4, 9).
 (a2) race timing: host-only, digital outputs only. Two protocol runs with the calibration input x = 0 (pedestal only),
      nominal V1, and C2 levels V2a < V2b; the host times the first output (na) edge after C2 starts.
      Square law: t ~ 1/(3.3 - V2 - V_th)^2 -> r = sqrt(t_b/t_a), |V_th| = (r*B - A)/(r - 1), A = 3.3-V2a, B = 3.3-V2b.
      Two-step version (the one evaluated): step 1 with V2 = RACE_V2_STEP1; step 2 with V2 = 3.3 - est1 - RACE_OV_STEP2,
      each step offset-corrected with its own nominal-die value (4 calibration races per die).
All three: offset correction = raw estimate on the nominal die (|V_th| 0.65, mu x1, no mismatch) minus 0.65, a
design-time constant (DECISIONS E5)."""
import json, pathlib, re, subprocess
import numpy as np
import eh, common as C

REP_W, REP_L = 300.0, 54.0
REP_VSG = (1.4, 1.7, 2.0)
SUP_I1 = 5e-6          # A, total over the crossbar (about 1 uA per rail)
SUP_RAMP = (300.0, 4300.0, 1.3)   # ramp start, end (us), final row level (V)
SUP_PHIB_OFF = 290.0              # us: sampler (phib) switched off before the ramp
RACE_V2 = (1.9, 2.1)          # single-step a2 (first test only)
RACE_V2_STEP1 = (1.8, 2.0)    # two-step a2, step 1 (coarse, finishes at every corner tested)
RACE_OV_STEP2 = (0.45, 0.30)  # two-step a2, step 2: V2 = 3.3 - estimate1 - overdrive


def model_lines(cn):
    lib = f".lib {cn[0]} {cn[1]}" if cn else f".lib {C.REPO}/rev10/sim/models/fitc10.lib fitc10"
    return f".include {C.REPO}/rev10/sim/models/trace2_otft_v2.sub\n{lib}\n"


def replica(vth=0.65, muf=1.0, dvth=0.0, tag="rep"):
    """DC: drain current at the two V_SG points (and a full curve for the record)."""
    cn = eh.corner(vth, muf)
    wd = C.workdir("eh_rep")
    out = {}
    for k, vsg in enumerate(REP_VSG):
        net = wd / f"{tag}_{k}.cir"
        net.write_text(f"* replica TFT measurement\n{model_lines(cn)}VS reps 0 DC 3.3\nVG repg 0 DC {3.3 - vsg:.4f}\nVD repd 0 DC 0\n"
                       f"XREP repd repg reps potft W={REP_W:g} L={REP_L:g} DVTH={dvth:.6f}\n"
                       ".options RELTOL=1e-6 ABSTOL=1e-15\n.control\nop\nprint i(vd)\nquit\n.endc\n.end\n")
        r = subprocess.run(["ngspice", "-b", net.name], cwd=wd, capture_output=True, text=True, timeout=120)
        m = re.search(r"i\(vd\)\s*=\s*([-+0-9.eE]+)", r.stdout)
        out[vsg] = abs(float(m.group(1)))
        net.unlink()
    raw = three_point(REP_VSG, [out[v] for v in REP_VSG])
    return dict(I_uA={str(k): v * 1e6 for k, v in out.items()}, vth_raw=raw,
                max_VGS_V=max(REP_VSG), max_VGD_V=3.3 - min(REP_VSG))


def three_point(V, I):
    """sqrt(I) = a*V - a*Vth - a*R*I, linear in (a, a*Vth, a*R): exact solve for 3 points."""
    V, I = np.asarray(V, float), np.asarray(I, float)
    A = np.column_stack([V, -np.ones(3), -I])
    a, aV, aR = np.linalg.solve(A, np.sqrt(I))
    return float(aV / a)


def supply(tag, outdir, vth=0.65, muf=1.0, mc=None):
    """Transient on the classifier die (Variant 3, unchanged circuit) with the a1 host sequence."""
    wd = C.workdir("eh_sup")
    net = wd / f"{tag}.cir"
    b = eh.build(net, 0, vth=vth, muf=muf, mc=mc, inst=False)
    t = net.read_text()
    t0, t1, vend = SUP_RAMP
    for i in range(1, 7):
        t, n = re.subn(rf"^(VR{i}\s+row{i}\s+0\s+).*$", rf"\g<1>PWL(0 3.3 {t0}u 3.3 {t1}u {vend})", t, flags=re.M); assert n == 1
    t, n = re.subn(r"^V_RSTR\s.*$", "V_RSTR rstr 0 PWL(0 3.3 20u 0)", t, flags=re.M); assert n == 1
    # sampler as in the normal protocol during reset (phib low), off from 290 us, before the ramp (E8 amendment:
    # with phib high from t = 0 the transient stalled at its start on die an35_d01)
    t, n = re.subn(r"^V_PHIB\s.*$", f"V_PHIB phib 0 PWL(0 0 {SUP_PHIB_OFF}u 0 {SUP_PHIB_OFF+1}u 3.3)", t, flags=re.M); assert n == 1
    t, n = re.subn(r"^V_PHI\s.*$", f"V_PHI phi 0 PWL(0 3.3 {SUP_PHIB_OFF}u 3.3 {SUP_PHIB_OFF+1}u 0)", t, flags=re.M); assert n == 1
    t, n = re.subn(r"^\.tran .*$", f".tran 100n {t1:.0f}u 0 100n", t, flags=re.M); assert n == 1
    net.write_text(t)
    vecs = ["v(row1)", "i(vdd)"] + [f"v({n})" for n in ("ref", "vls") + tuple(f"ap{k}" for k in range(1, 6))
                                    + tuple(f"na{k}" for k in range(1, 6)) + tuple(f"d{k}" for k in range(1, 6))]
    try:
        d, info = eh.simulate(net, tag, vecs)
    except subprocess.TimeoutExpired:
        d, info = None, dict(error="timeout (7200 s)")
    net.unlink()
    if d is None:   # simulation did not finish: the method gives no estimate on this die (reported as a failure)
        rec = dict(tag=tag, vth=vth, muf=muf, mc=mc, run=info, vth_raw=None, vsg_at_I=None, na_max_during_ramp={0: None}, failed=True)
        outdir = pathlib.Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
        (outdir / f"{tag}.json").write_text(json.dumps(rec, indent=1, default=float))
        return rec
    tt = d["time"]
    idd = -d["i(vdd)"]
    base = float(np.mean(idd[(tt > 293e-6) & (tt < 300e-6)]))   # after the phib edge at 290 us
    m = tt > t0 * 1e-6
    vsg = 3.3 - d["v(row1)"][m]
    di = idd[m] - base
    # first crossing of each target current (dI rises monotonically with V_SG apart from small ripple)
    def vsg_at(I):
        k = np.where(di >= I)[0]
        if not len(k):
            return None
        k = k[0]
        return float(np.interp(I, [di[k - 1], di[k]], [vsg[k - 1], vsg[k]]))
    vs = [vsg_at(k * SUP_I1) for k in (1, 4, 9)]
    va, vb = vs[0], vs[1]
    raw = three_point(vs, [k * SUP_I1 for k in (1, 4, 9)]) if all(vs) else None
    na_max = {k: float(np.max(d[f"v(na{k})"][m])) for k in range(1, 6)}
    # decimated curve for the record
    g = np.linspace(t0 * 1e-6, t1 * 1e-6, 401)
    rec = dict(tag=tag, vth=vth, muf=muf, mc=mc, run=info, I_base_uA=base * 1e6, vsg_at_I=vs, vth_raw=raw,
               na_max_during_ramp=na_max, ap_max=float(max(np.max(d[f"v(ap{k})"][m]) for k in range(1, 6))),
               curve=dict(vsg=list(3.3 - np.interp(g, tt, d["v(row1)"])), dI_uA=list((np.interp(g, tt, idd) - base) * 1e6),
                          ref=list(np.interp(g, tt, d["v(ref)"]))))
    outdir = pathlib.Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"{tag}.json").write_text(json.dumps(rec, indent=1, default=float))
    return rec


def race_jobs(tagp, outdir, vth=0.65, muf=1.0, mc=None, V2s=RACE_V2):
    """The two a2 calibration runs (eh.run jobs). x = 0; V1 = nominal 1.82 V; idx 0 only labels the json."""
    return [dict(tag=f"{tagp}_V2_{round(v*1000):04d}", idx=0, x=np.zeros(6), outdir=outdir, wdir="race", vth=vth, muf=muf,
                 mc=mc, V2=v, inst=False, save_wave=False, vth_metric=vth) for v in V2s]


def race2_step2_levels(vth_est1):
    return tuple(round(3.3 - vth_est1 - ov, 3) for ov in RACE_OV_STEP2)


def race_estimate(m_a, m_b, V2s=RACE_V2):
    ta, tb = m_a.get("race_us"), m_b.get("race_us")
    if not ta or not tb or ta <= 0 or tb <= 0:
        return dict(t_us=[ta, tb], vth_raw=None)
    r = np.sqrt(tb / ta)
    A, B = 3.3 - V2s[0], 3.3 - V2s[1]
    return dict(t_us=[ta, tb], vth_raw=float((r * B - A) / (r - 1)))
