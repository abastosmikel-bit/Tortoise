"""Shared helpers for the scheme-A weight-retraining study (results/weights_schemeA).

Everything circuit-related is imported from the fitc10 campaign (results/fitc10_campaign/scripts/common.py,
Variant 3 = main design) and the frozen base-design builder (rev10/sim/tools). Nothing in those folders is modified.
What this module adds:
  * the finger matrix is a per-job argument (the frozen builder reads a module global `t11.F`; it is set per build);
  * jobs can use training samples (split="train") or test samples (split="test");
  * host timing (T1, WMIN, GAP, V1, V2) is a per-job argument (default = the frozen protocol);
  * size-scaled V_th mismatch whose die draws are paired with the old campaign's dies (same seed -> the same
    z-score for every instance that exists in both builds; see apply_mc_paired).
`build()` reproduces common.build() byte for byte for the default arguments (checked by scripts/check_tooling.py).
"""
import gzip, json, os, pathlib, re, sys
sys.dont_write_bytecode = True
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_v, "1")          # one thread per process: the SPICE workers need the cores
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
WS = HERE.parent                                   # results/weights_schemeA
REPO = WS.parents[1]
CAMP = REPO / "results/fitc10_campaign"
os.environ["FC10_VARIANT"] = "3"                   # main design (D11 of the campaign)
sys.path.insert(0, str(CAMP / "scripts"))
import common as C                                 # noqa: E402  campaign helpers (build/simulate/metrics/save)
import build_A                                     # noqa: E402  frozen builder (same module object common uses)
import t11                                         # noqa: E402  holds the finger matrix global F used by the builder

D = np.load(REPO / "data/trace2_data.npz")
XTR, YTR, XTE, YTE = D["X_train"], D["y_train"], D["X_test"], D["y_test"]   # y 0-based; netlist classes 1..5
GTR = D["group_train"]
F_OLD = np.load(REPO / "rev10/eval/F_hw_m4_firstpass.npy").astype(int)
RAW, SUMM, WEIGHTS = WS / "raw", WS / "summary", WS / "weights"
VARIANT = 3
TIMING0 = dict(T1=170.0, WMIN=20.0, GAP=5.0, V1off=0.83, V2off=0.25)   # frozen host protocol (docs/TOOLING.md)
VTH_NOM = 0.65
# Borrowed lab-corner prior the campaign started every warm-start chain from (gateB.PRIOR). Our warm starts are
# built from it with TRAINING samples only (DECISIONS.md W6); the campaign's fitc10 warm start is never used.
LAB_PRIOR = C.W / "sim/circuits/t6L_x2_v085"


def X_of(split):
    return XTR if split == "train" else XTE


def Y_of(split):
    return YTR if split == "train" else YTE


def load_F(F):
    if isinstance(F, (str, pathlib.Path)):
        F = np.load(F)
    F = np.asarray(F).astype(int)
    assert F.shape == (6, 5) and (F >= 0).all() and (F.sum(0) <= 60).all() and (F.sum(0) >= 50).all(), F   # W1, W13
    return F


def n_tft(F):
    """134 TFTs with the old weights (9 empty banks removed): 113 non-crossbar + one instance per non-empty bank."""
    return 113 + int((np.asarray(F) > 0).sum())


# ----------------------------------------------------------------------------- build
def build(dst, x, prior, F, corner=None, mc=None, levels_vth=None, timing=None, trace=C.TRACE_US, perturb=None):
    """common.build (Variant 3) with the finger matrix F and optional host timing.
    timing: dict with any of T1, WMIN, GAP (us) and V1off, V2off (V; V1 = 3.3 - |V_th| - V1off, V2 = 3.3 - |V_th| - V2off,
    with |V_th| = levels_vth if given, else 0.65). Default = frozen protocol -> identical netlist to common.build."""
    dst = pathlib.Path(dst)
    tm = dict(TIMING0, **(timing or {}))
    vt = VTH_NOM if levels_vth is None else levels_vth
    t11.F = load_F(F)
    cwd = os.getcwd()
    os.chdir(dst.parent)
    try:
        kw = dict(T1=tm["T1"], WMIN=tm["WMIN"], GAP=tm["GAP"])
        # common.build passes no levels for the nominal case (build_A then uses its own 0.65 V formula, same values)
        if levels_vth is not None or tm["V1off"] != 0.83 or tm["V2off"] != 0.25:
            kw.update(V1=round(3.3 - vt - tm["V1off"], 3), V2=round(3.3 - vt - tm["V2off"], 3))
        tC2 = build_A.build(str(dst), x, str(prior), vth="065", TRACE=trace, **kw)
    finally:
        os.chdir(cwd)
    t = dst.read_text()
    t, n = re.subn(r"^(CRAIL[1-5]\s+ap[1-5]\s+0\s+)375\.0p",
                   lambda m: f"{m.group(1)}{C.CRAIL_PF * C.CRAIL_SCALE:.2f}p", t, flags=re.M)
    assert n == 5, n
    t, n = re.subn(r"^(CREF\s+ref\s+0\s+)24\.0p", lambda m: f"{m.group(1)}{C.CREF_PF * C.CRAIL_SCALE:.2f}p", t, flags=re.M)
    assert n == 1, n
    changed = []

    def load_resize(m):
        name, mid, L, rest = m.groups()
        Ln = float(L) * C.LOAD_L_SCALE
        changed.append((name, m.group(0).split()[3], float(re.search(r"W=(\S+)", mid).group(1)), float(L), Ln))
        return f"{name}{mid}{Ln:g}{rest}"
    t = re.sub(r"^(X\S+)(\s+0\s+0\s+\S+\s+potft\s+W=\S+\s+L=)(\S+)(.*)$", load_resize, t, flags=re.M)
    assert len(changed) == C.N_LOADS[VARIANT], changed
    if corner:
        t, n = re.subn(r"^\.lib \.\./models/fitc10\.lib fitc10$", f".lib ../models/{corner[0]} {corner[1]}", t, flags=re.M)
        assert n == 1
    draws = None
    if mc:
        mc = dict(mc)
        if mc.pop("paired", False):
            t, draws = apply_mc_paired(t, **mc)
        else:
            t, draws = C.apply_mc(t, **mc)
    if perturb:              # single-device V_th offsets (W4.3 sensitivity runs): {instance: DVTH [V]} on the base models
        assert not mc
        for nm, dv in perturb.items():
            t, n = re.subn(rf"^({re.escape(nm)}\s+\S+\s+\S+\s+\S+\s+potft(?:seg)?\s+W=\S+\s+L=\S+)", rf"\g<1> DVTH={dv:.5f}", t, flags=re.M)
            assert n == 1, (nm, n)
    changed.append(("CREF", "ref", None, C.CREF_PF, C.CREF_PF * C.CRAIL_SCALE))
    t = t.replace("TRACE-2 FINAL (frozen)", f"TRACE-2 FINAL (frozen) + fitc10 resize Variant {VARIANT}", 1)
    dst.write_text(t)
    return dict(tC2=tC2, changed=changed, draws=draws)


# ----------------------------------------------------------------------------- paired mismatch
_OLD = None


def _old_build_geometry():
    """Instance geometry {name: (W, L)} of the old-weights Variant 3 build: the instance set the old campaign's die
    draws were taken over (sorted-name order). Built once per process in a per-process file."""
    global _OLD
    if _OLD is None:
        wd = C.workdir("wsA_names_v3")
        net = wd / f"names_{os.getpid()}.cir"
        build(net, np.full(6, 0.5), LAB_PRIOR, F_OLD)
        txt = net.read_text()
        net.unlink()
        _OLD = {m.group(1): (float(m.group(2)), float(m.group(3))) for m in
                re.finditer(r"^(X\S+)\s+\S+\s+\S+\s+\S+\s+potft(?:seg)?\s+W=(\S+)\s+L=(\S+)", txt, re.M)}
    return _OLD


def apply_mc_paired(t, seed, s_vth, s_mu=0.10, s_rc=0.20, scale="pelgrom_vth"):
    """Size-scaled V_th-only mismatch (the campaign's D13 / 3B-V model) with draws paired to the old campaign's dies.
    The old dies drew, for each instance of the OLD build in sorted-name order, rng.normal for DVTH, KMU, KRC.
    Here the same rng sequence is replayed over the old instance list to recover each instance's z-score
    z = DVTH_old / sigma_old; an instance of the new build gets DVTH = z * s_vth * sqrt(780/(W*L)) with ITS OWN W*L
    (crossbar banks change width with the finger count). Crossbar banks that are empty in the old weights get
    z-scores from a separate stream (default_rng(seed + 7_000_000), banks X1..X30 in numeric order).
    KMU = KRC = 1 (V_th only), as in 3B-V."""
    assert scale == "pelgrom_vth"
    geo = {m.group(1): (float(m.group(2)), float(m.group(3))) for m in
           re.finditer(r"^(X\S+)\s+\S+\s+\S+\s+\S+\s+potft(?:seg)?\s+W=(\S+)\s+L=(\S+)", t, re.M)}
    old_geo = _old_build_geometry()
    old = sorted(old_geo)
    rng = np.random.default_rng(seed)
    z = {}
    for nm in old:
        f = float(np.sqrt(780.0 / (old_geo[nm][0] * old_geo[nm][1])))
        dv = float(rng.normal(0, s_vth * f)); rng.normal(1, s_mu * f); rng.normal(0, s_rc * f)
        z[nm] = dv / (s_vth * f)
    rng2 = np.random.default_rng(seed + 7_000_000)
    extra = {f"X{j}": float(rng2.standard_normal()) for j in range(1, 31)}
    draws = {}
    for nm in sorted(geo):
        f = float(np.sqrt(780.0 / (geo[nm][0] * geo[nm][1])))
        zz = z[nm] if nm in z else extra[nm]
        draws[nm] = dict(DVTH=float(zz * s_vth * f), KMU=1.0, KRC=1.0, sigma_factor=round(f, 5), z=zz, paired=nm in z)

    def add(m):
        d = draws[m.group(1)]
        return f"{m.group(0)} DVTH={d['DVTH']:.5f} KMU={d['KMU']:.5f} KRC={d['KRC']:.5f}"
    t, n = re.subn(r"^(X\S+)\s+\S+\s+\S+\s+\S+\s+potft(?:seg)?\s+W=\S+\s+L=\S+", add, t, flags=re.M)
    assert n == len(geo)
    t = t.replace(".include ../models/trace2_otft_v2.sub", ".include ../models/trace2_otft_v2_mc.sub")
    t = t.replace(".include ../models/trace2_otft_seg.sub", ".include ../models/trace2_otft_seg_mc.sub")
    return t, draws


# ----------------------------------------------------------------------------- run
def run_one(job):
    """job: dict(tag, split, idx, F, prior, outdir[, wdir, corner, mc, levels_vth, timing, vth, save_prior, audit,
    nodes, dec_us, extra]). Writes <tag>.json, <tag>.csv.gz, <tag>.cir.gz (+ _draws.json) to outdir."""
    split = job.get("split", "train")
    x = X_of(split)[job["idx"]]
    F = load_F(job["F"])
    wd = C.workdir(f'{job.get("wdir", "wsA")}_v{VARIANT}')
    net = wd / f"{job['tag']}.cir"
    b = build(net, x, job["prior"], F, corner=job.get("corner"), mc=job.get("mc"), levels_vth=job.get("levels_vth"),
              timing=job.get("timing"), perturb=job.get("perturb"))
    t, v, info = C.simulate(net, job["tag"], audit=job.get("audit", False))
    meta = dict(tag=job["tag"], split=split, idx=job["idx"], label=int(Y_of(split)[job["idx"]]) + 1,
                F=F.tolist(), weights=job.get("weights_name"), prior=str(job["prior"]), variant=VARIANT,
                trace_us=C.TRACE_US, corner=job.get("corner"), mc={k: v_ for k, v_ in (job.get("mc") or {}).items()} or None,
                levels_vth=job.get("levels_vth"), timing=dict(TIMING0, **(job.get("timing") or {})), run=info,
                perturb=job.get("perturb"),
                n_tft=sum(1 for l in net.read_text().splitlines() if re.match(r"^X\S+\s.*potft", l)),
                x=[round(float(a), 6) for a in x])
    if t is not None:
        meta.update(C.metrics(t, v, b["tC2"], vth=job.get("vth", VTH_NOM)))
        meta["c2_slope_mV_per_us"] = c2_slopes(t, v, b["tC2"], meta)
        if job.get("save_prior"):
            C.save_prior(job["save_prior"], t, v)
    outdir = pathlib.Path(job["outdir"])
    C.save_run(outdir, job["tag"], t, v, meta)
    with open(net) as f, gzip.open(outdir / f"{job['tag']}.cir.gz", "wt") as g:
        g.write(f.read())
    if b["draws"]:
        (outdir / f"{job['tag']}_draws.json").write_text(json.dumps(b["draws"]))
    if not job.get("audit"):          # the stress audit needs the netlist to map device terminals
        try:
            net.unlink()
        except FileNotFoundError:
            pass
    return meta


def c2_slopes(t, v, tC2_us, meta):
    """Per-class rail slope in C2 (mV/us), measured over the 40 us window ending at the first trip (or at C2 + 200 us
    if nothing tripped), starting no earlier than C2 + 20 us."""
    tw = min(meta["trip_us"].values()) * 1e-6 if meta.get("trip_us") else (tC2_us + 200) * 1e-6
    t1 = tw
    t0 = max(tC2_us * 1e-6 + 20e-6, t1 - 40e-6)
    if t1 - t0 < 5e-6:
        return None
    at = lambda n, tt: float(np.interp(tt, t, v[n]))
    return {k: round((at(f"ap{k}", t1) - at(f"ap{k}", t0)) / ((t1 - t0) * 1e6) * 1e3, 5) for k in range(1, 6)}


def load_runs(sub):
    out = []
    for f in sorted((RAW / sub).glob("*.json")):
        if f.name.endswith("_draws.json"):
            continue
        out.append(json.loads(f.read_text()))
    return out


def wilson(k, n, z=1.96):
    import math
    if n == 0:
        return (None, None)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(round(c - h, 6), 0.0) + 0.0, min(round(c + h, 6), 1.0))   # 6 decimals: the report rounds once (audit finding 2)
