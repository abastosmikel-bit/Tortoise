"""Shared helpers for the fitc10 campaign: build (Variant 1/2 resize), simulate, measure, save.

Build = frozen base-design builder `build_A.build(..., vth="065")` (base netlist t5L_x2_v065.cir, corner
fitc10.lib, V1/V2 from the V_th-referenced formula), then the fitc10 resize decided by the project owner
on 2026-10-22 (see DECISIONS.md):
  * CRAIL1-5 x5.87 (375 pF -> 2201.25 pF). CREF and all other caps unchanged.
  * Variant 1: every TFT with drain = 0 and gate = 0 in the final build gets L x6, W unchanged (19 devices).
  * Variant 2: the same, but only the logic-chain loads (X82/X84/X87 families, XI2, X80; 17 devices).
  * Variant 3 (owner's proposed correction to D3, 2026-10-22): Variant 1 + CREF x5.87 (24 pF -> 140.88 pF).
Simulation settings are the RELAX=1 solver set (docs/TOOLING.md); the race window is TRACE us after the start of C2.
"""
import gzip, json, os, pathlib, re, subprocess, sys, time
import numpy as np

CAMP = pathlib.Path(__file__).resolve().parents[1]
REPO = CAMP.parents[1]
W = pathlib.Path("/home/claude/w")
sys.path.insert(0, str(W / "sim/tools"))
os.environ.setdefault("FINGERS", str(REPO / "rev10/eval/F_hw_m4_firstpass.npy"))
import build_A  # noqa: E402  (frozen base-design builder)

D = np.load(REPO / "data/trace2_data.npz")
XTE, YTE = D["X_test"], D["y_test"]          # y is 0-based; netlist classes are 1..5
F = np.load(REPO / "rev10/eval/F_hw_m4_firstpass.npy").astype(int)

# Variant selection for the phase scripts (D11): Variant 1 outputs live in raw/, summary/ (as first run);
# any other variant in raw/v<N>/, summary/v<N>/. Set FC10_VARIANT=3 for the main (adopted) design.
VAR = int(os.environ.get("FC10_VARIANT", "1"))
RAW = CAMP / "raw" if VAR == 1 else CAMP / f"raw/v{VAR}"
SUMM = CAMP / "summary" if VAR == 1 else CAMP / f"summary/v{VAR}"
SUMM.mkdir(parents=True, exist_ok=True)

CRAIL_PF, CRAIL_SCALE, LOAD_L_SCALE = 375.0, 5.87, 6
VARIANT2_SET = ({f"X{82 + 10 * c}" for c in range(5)} | {f"X{84 + 10 * c}" for c in range(5)}
                | {f"X{87 + 10 * c}" for c in range(5)} | {"XI2", "X80"})
N_LOADS = {1: 19, 2: 17, 3: 19}
CREF_PF = 24.0
TRACE_US = 2500.0                              # race window after C2 start (D6 amendment; specification: >= 1.2 ms)
RELAX = ".options RELTOL=1e-3 ABSTOL=1e-12 VNTOL=1e-6 CHGTOL=1e-14 ITL4=100 METHOD=GEAR MAXORD=2"
WARM_NODES = ([f"ap{i}" for i in range(1, 6)] + [f"na{i}" for i in range(1, 6)] + [f"nb{i}" for i in range(1, 6)]
              + [f"d{i}" for i in range(1, 6)] + ["ref", "win", "lockb", "vls"])
TIMING = ["rstr", "rstb", "phib", "phi"]
NODES = WARM_NODES + TIMING
T_ON = 320e-6           # score.py convention for scheme A: trips counted after 320 us
T_RESET_SAMPLE = 311e-6  # rail reset level read just before rstr releases (311.5 us)
DEC_US = 1.0            # saved waveform resolution


# ----------------------------------------------------------------------------- build
def workdir(name):
    """A run directory under /home/claude/w/sim (so ../models and ../tools resolve) with base netlists linked."""
    d = W / "sim" / name
    d.mkdir(parents=True, exist_ok=True)
    for f in (REPO / "rev10/sim/circuits").glob("t5L_x2_v*.cir"):
        p = d / f.name
        if not p.exists():
            try:
                p.symlink_to(f)
            except FileExistsError:      # another worker created it first
                pass
    return d


def build(dst, idx=None, prior=None, variant=1, trace=TRACE_US, corner=None, mc=None, x=None, levels_vth=None):
    """Build a fitc10 netlist. prior: absolute tag (path without .dat/.cols) of the warm-start state.
    corner: (libfile, section) to replace the fitc10 corner line. mc: dict(seed, s_vth, s_mu, s_rc[, scale]).
    levels_vth: if set, the host row levels are re-trimmed with build_A's own formula for that |V_th|
    (V1 = 3.3 - |V_th| - 0.83 for calibration and C1, V2 = 3.3 - |V_th| - 0.25 for C2); default = the 0.65 V levels.
    Returns dict with tC2 (us), changed devices and MC draws."""
    dst = pathlib.Path(dst)
    x = XTE[idx] if x is None else x
    cwd = os.getcwd()
    os.chdir(dst.parent)
    try:
        lv = {} if levels_vth is None else dict(V1=round(3.3 - levels_vth - 0.83, 3), V2=round(3.3 - levels_vth - 0.25, 3))
        tC2 = build_A.build(str(dst), x, str(prior), vth="065", TRACE=trace, **lv)
    finally:
        os.chdir(cwd)
    t = dst.read_text()
    t, n = re.subn(r"^(CRAIL[1-5]\s+ap[1-5]\s+0\s+)375\.0p",
                   lambda m: f"{m.group(1)}{CRAIL_PF * CRAIL_SCALE:.2f}p", t, flags=re.M)
    assert n == 5, n
    if variant == 3:
        t, n = re.subn(r"^(CREF\s+ref\s+0\s+)24\.0p", lambda m: f"{m.group(1)}{CREF_PF * CRAIL_SCALE:.2f}p", t, flags=re.M)
        assert n == 1, n
    changed = []

    def load_resize(m):
        name, mid, L, rest = m.groups()
        if variant == 2 and name not in VARIANT2_SET:
            return m.group(0)
        Ln = float(L) * LOAD_L_SCALE
        changed.append((name, m.group(0).split()[3], float(re.search(r"W=(\S+)", mid).group(1)), float(L), Ln))
        return f"{name}{mid}{Ln:g}{rest}"
    t = re.sub(r"^(X\S+)(\s+0\s+0\s+\S+\s+potft\s+W=\S+\s+L=)(\S+)(.*)$", load_resize, t, flags=re.M)
    assert len(changed) == N_LOADS[variant], changed
    if corner:
        t, n = re.subn(r"^\.lib \.\./models/fitc10\.lib fitc10$", f".lib ../models/{corner[0]} {corner[1]}", t, flags=re.M)
        assert n == 1
    draws = None
    if mc:
        t, draws = apply_mc(t, **mc)
    if variant == 3:
        changed.append(("CREF", "ref", None, CREF_PF, CREF_PF * CRAIL_SCALE))
    t = t.replace("TRACE-2 FINAL (frozen)", f"TRACE-2 FINAL (frozen) + fitc10 resize Variant {variant}", 1)
    dst.write_text(t)
    return dict(tC2=tC2, changed=changed, draws=draws)


def apply_mc(t, seed, s_vth, s_mu=0.10, s_rc=0.20, scale="flat"):
    """Independent per-device draws on every TFT (crossbar included): DVTH ~ N(0, s_vth) [V, same for every
    geometry - an assumption], mobility factor KMU ~ N(1, s_mu) (clipped at 0.2), contact factor
    KRC ~ lognormal(sigma = s_rc). Draws are keyed by instance name in sorted order, so a die is the same
    for every sample. Uses the *_mc model files (identical equations, two extra instance multipliers)."""
    geo = {m.group(1): (float(m.group(2)), float(m.group(3))) for m in
           re.finditer(r"^(X\S+)\s+\S+\s+\S+\s+\S+\s+potft(?:seg)?\s+W=(\S+)\s+L=(\S+)", t, re.M)}
    names = sorted(geo)
    rng = np.random.default_rng(seed)
    draws = {}
    for nm in names:
        # scale="pelgrom": every sigma x sqrt(780 um^2 / (W*L)) (build_final.py convention; s_* are the anchors).
        # The rng call order is the same as "flat", so a given seed gives the same underlying z-scores.
        f = 1.0 if scale == "flat" else float(np.sqrt(780.0 / (geo[nm][0] * geo[nm][1])))   # pelgrom, pelgrom_vth
        draws[nm] = dict(DVTH=float(rng.normal(0, s_vth * f)), KMU=float(max(rng.normal(1, s_mu * f), 0.2)),
                         KRC=float(np.exp(rng.normal(0, s_rc * f))), sigma_factor=round(f, 5))
        if scale == "pelgrom_vth":
            # V_th-only size-scaled mismatch (D13): the mu and R_C draws are still taken (so the V_th draws are
            # identical to scale="pelgrom" for the same seed) but not applied: KMU = KRC = 1 (nominal).
            draws[nm].update(KMU=1.0, KRC=1.0)

    def add(m):
        d = draws[m.group(1)]
        return f"{m.group(0)} DVTH={d['DVTH']:.5f} KMU={d['KMU']:.5f} KRC={d['KRC']:.5f}"
    t, n = re.subn(r"^(X\S+)\s+\S+\s+\S+\s+\S+\s+potft(?:seg)?\s+W=\S+\s+L=\S+", add, t, flags=re.M)
    assert n == len(names), (n, len(names))
    t = t.replace(".include ../models/trace2_otft_v2.sub", ".include ../models/trace2_otft_v2_mc.sub")
    t = t.replace(".include ../models/trace2_otft_seg.sub", ".include ../models/trace2_otft_seg_mc.sub")
    return t, draws


# ----------------------------------------------------------------------------- simulate
def simulate(net, tag, nodes=NODES, audit=False, timeout=3600):
    """Run ngspice on net (directory = its parent). Returns (t, {node: v}, info). audit=True also writes
    an ASCII raw of every top-level node (for audit.py) as <tag>.raw."""
    net = pathlib.Path(net)
    txt = re.sub(r"(?is)^\.control.*?^\.endc\s*$", "", net.read_text(), flags=re.M)
    top = sorted({n.lower() for l in txt.splitlines() if re.match(r"^[XxMmCcRrVv]", l)
                  for n in l.split()[1:4] if re.match(r"^[a-z_][a-z0-9_]*$", n.lower())
                  and n.lower() not in ("potft", "potftseg", "pwl", "dc")})
    ctl = [RELAX, ".control", "set filetype=ascii", "run",
           f"wrdata {tag}.dat " + " ".join(f"v({n})" for n in nodes)]
    if audit:
        ctl.append(f"write {tag}.raw " + " ".join(f"v({n})" for n in top))
    ctl += ["quit", ".endc"]
    i = txt.rstrip().rfind("\n.end")
    assert txt[i:].strip().lower() == ".end"
    run = net.with_name(f"_{tag}.cir")
    run.write_text(txt[:i] + "\n" + "\n".join(ctl) + txt[i:])
    s = time.time()
    r = subprocess.run(["ngspice", "-n", run.name], cwd=run.parent, capture_output=True, text=True,
                       timeout=timeout, stdin=subprocess.DEVNULL)
    wall = time.time() - s
    log = r.stdout + r.stderr
    warn = [l.strip() for l in log.splitlines() if re.search(r"error|abort|singular|too small|failed", l, re.I)]
    dat = run.with_name(f"{tag}.dat")
    info = dict(wall_s=round(wall, 1), returncode=r.returncode, warnings=warn[:20])
    if not dat.exists():
        info["error"] = "no data"
        return None, None, info
    d = np.loadtxt(dat)
    t = d[:, 0]
    v = {n: d[:, 2 * k + 1] for k, n in enumerate(nodes)}
    dat.unlink()
    run.unlink()
    return t, v, info


# ----------------------------------------------------------------------------- measure
def _cross(t, x, lev, after, rising=True):
    m = (t > after)[1:]
    c = (x[:-1] < lev) & (x[1:] >= lev) if rising else (x[:-1] > lev) & (x[1:] <= lev)
    i = np.where(m & c)[0]
    if not len(i):
        return None
    i = i[0]
    return float(t[i] + (lev - x[i]) * (t[i + 1] - t[i]) / (x[i + 1] - x[i]))   # linear interpolation


def metrics(t, v, tC2_us, vth=0.65):
    """Per-run outcome. Classes are 1..5. Valid = exactly one class latched (na > 2.5 V at the end) and it is
    the first class whose na crossed 1.65 V after 320 us (score.py definition)."""
    tend = t[-1]
    trips = {k: _cross(t, v[f"na{k}"], 1.65, T_ON) for k in range(1, 6)}
    trips = {k: x for k, x in trips.items() if x is not None and x < tend - 1e-6}
    latched = [k for k in range(1, 6) if v[f"na{k}"][-1] > 2.5]
    lock = _cross(t, v["win"], 2.05, T_ON)
    first = min(trips, key=trips.get) if trips else None
    tw = trips[first] if first else None
    if not trips:
        fail = "timeout"          # nothing tripped inside the window
    elif not latched:
        fail = "none_latched"
    elif len(latched) > 1:
        fail = "multi_latched"
    elif latched[0] != first:
        fail = "latched_not_first"
    else:
        fail = None
    out = dict(trip_us={k: round(x * 1e6, 3) for k, x in trips.items()}, first=first, latched=latched,
               winner=latched[0] if len(latched) == 1 else None, valid=fail is None, failure=fail,
               lock_us=round(lock * 1e6, 3) if lock else None,
               lock_latency_us=round((lock - tw) * 1e6, 3) if (lock and tw and lock > tw) else None,
               trip_in_C1=bool(tw is not None and tw < tC2_us * 1e-6), tC2_us=tC2_us, t_end_us=round(tend * 1e6, 1))
    lockb_on = _cross(t, v["lockb"], 3.3 - vth, T_ON, rising=False)
    out["lockb_chain_us"] = round((lockb_on - tw) * 1e6, 3) if (lockb_on and tw and lockb_on > tw) else None
    # rail levels at the end of reset, and at the end of C1
    at = lambda n, tt: float(np.interp(tt, t, v[n]))
    out["reset_level"] = {k: round(at(f"ap{k}", T_RESET_SAMPLE), 5) for k in range(1, 6)}
    out["ref_reset"] = round(at("ref", T_RESET_SAMPLE), 5)
    # ref settling at the end of calibration sampling (phib rises 309-310 us): change over 308-309 us
    out["ref_308"], out["ref_309"] = round(at("ref", 308e-6), 5), round(at("ref", 309e-6), 5)
    out["ref_settle_mV_308_309"] = round((at("ref", 309e-6) - at("ref", 308e-6)) * 1e3, 3)
    out["rail_at_C2"] = {k: round(at(f"ap{k}", tC2_us * 1e-6), 5) for k in range(1, 6)}
    # runner-up gap: the rails keep charging after the lock, so measure when each losing rail reaches the
    # level the first tripper's rail had at its trip (direct), and the same gap from the local slope.
    if tw is not None:
        vstar = at(f"ap{first}", tw)
        gaps = {}
        for k in range(1, 6):
            if k == first:
                continue
            dv = vstar - at(f"ap{k}", tw)
            sl = (at(f"ap{k}", tw) - at(f"ap{k}", tw - 10e-6)) / 10e-6
            reach = _cross(t, v[f"ap{k}"], vstar, tw) if dv > 0 else tw
            gaps[k] = dict(dV_mV=round(dv * 1e3, 3), gap_reach_us=round((reach - tw) * 1e6, 3) if reach else None,
                           gap_slope_us=round(dv / sl * 1e6, 3) if sl > 0 else None)
        ru = min(gaps, key=lambda k: gaps[k]["dV_mV"])
        out.update(runner_up=ru, gap=gaps[ru], gaps=gaps)
    else:
        out.update(runner_up=None, gap=None, gaps=None)
    return out


# ----------------------------------------------------------------------------- save
def save_run(outdir, tag, t, v, meta, nodes=NODES, dec_us=DEC_US):
    """Write <tag>.json (metrics + run info) and <tag>.csv.gz (waveforms resampled every dec_us)."""
    outdir = pathlib.Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"{tag}.json").write_text(json.dumps(meta, indent=1, default=float))
    if t is not None:
        tg = np.arange(0, t[-1] + 1e-12, dec_us * 1e-6)
        cols = [tg * 1e6] + [np.interp(tg, t, v[n]) for n in nodes]
        with gzip.open(outdir / f"{tag}.csv.gz", "wt") as f:
            f.write("t_us," + ",".join(nodes) + "\n")
            np.savetxt(f, np.column_stack(cols), fmt="%.4f", delimiter=",")


def save_prior(path_tag, t, v):
    """Save the end state in the .dat/.cols format t10.py's warm start reads (last 5 rows)."""
    p = pathlib.Path(str(path_tag))
    p.parent.mkdir(parents=True, exist_ok=True)
    cols = [n for n in WARM_NODES if n in v]
    rows = []
    for i in range(len(t) - 5, len(t)):
        r = []
        for n in cols:
            r += [t[i], v[n][i]]
        rows.append(r)
    np.savetxt(str(p) + ".dat", np.array(rows), fmt="%.6e")
    pathlib.Path(str(p) + ".cols").write_text(" ".join(cols))


def run_one(job):
    """job: dict(tag, idx, prior, variant, outdir, wdir, [corner], [mc], [expect], [save_prior], [audit])."""
    wd = workdir(f'{job.get("wdir", "runs")}_v{job.get("variant", 1)}')
    net = wd / f"{job['tag']}.cir"
    b = build(net, job["idx"], job["prior"], job.get("variant", 1), trace=job.get("trace", TRACE_US),
              corner=job.get("corner"), mc=job.get("mc"), levels_vth=job.get("levels_vth"))
    t, v, info = simulate(net, job["tag"], audit=job.get("audit", False))
    meta = dict(tag=job["tag"], idx=job["idx"], label=int(YTE[job["idx"]]) + 1, prior=str(job["prior"]),
                variant=job.get("variant", 1), trace_us=job.get("trace", TRACE_US), corner=job.get("corner"),
                mc=job.get("mc"), levels_vth=job.get("levels_vth"), run=info,
                n_tft=sum(1 for l in net.read_text().splitlines() if re.match(r"^X\S+\s.*potft", l)),
                resized=b["changed"])
    if t is not None:
        meta.update(metrics(t, v, b["tC2"], vth=job.get("vth", 0.65)))
        if job.get("save_prior"):
            save_prior(job["save_prior"], t, v)
    outdir = pathlib.Path(job["outdir"])
    save_run(outdir, job["tag"], t, v, meta)
    with open(net) as f, gzip.open(outdir / f"{job['tag']}.cir.gz", "wt") as g:
        g.write(f.read())
    if b["draws"]:
        (outdir / f"{job['tag']}_draws.json").write_text(json.dumps(b["draws"]))
    return meta
