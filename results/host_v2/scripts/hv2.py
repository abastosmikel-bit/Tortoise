"""Host protocol v2 tooling (results/host_v2). Imports the fitc10 campaign and energy_host tooling read-only.

Circuit: Variant 3 at fitc10, weights rev10/eval/F_hw_m4_firstpass.npy (unchanged; eh.build is reused). Only the
host protocol changes. Every rule and constant used here is defined in DECISIONS.md (H-sections); the constants below
are the frozen values once DECISIONS.md H2 is committed.

Classification netlist (build_cls):
  eh.build(..., cold=True, rstb_rel=RSTB_REL, reset_ext=RESET_BASE*(k-1), T1=T1_BASE*k, trace=WINDOW_BASE*k)
  + an ideal host model (B-sources, not part of the die): D us after the first output na > 1.65 V (counted from
    320 us + reset extension) every row returns to 3.3 V (0.2 us edge); outputs are read READ us later.
  + optional prior state (.ic of the saved nodes) for a power-up that follows a finite VDD-off period.
  ngspice stops the transient STOP_TAIL us after the read time ('stop when'), to save compute.
"""
import gzip, json, os, pathlib, re, subprocess, sys, time
import numpy as np

HV = pathlib.Path(__file__).resolve().parents[1]
REPO = HV.parents[1]
sys.path.insert(0, str(REPO / "results/energy_host/scripts"))
import eh            # noqa: E402  (energy_host tooling, read-only; imports fitc10 common)
import common as C   # noqa: E402

RAW, SUMM = HV / "raw", HV / "summary"
# Corner .lib files: new corners are written here, never into results/energy_host/models (read-only folder). Corners
# that the energy/host study already wrote there are copied byte-identically on first use, so every netlist points into host_v2.
eh.MODELS = HV / "models"
eh.MODELS.mkdir(exist_ok=True)
_eh_corner = eh.corner


def _corner(vth=eh.VTH0, muf=1.0):
    sec = f"eh_v{round(vth * 1e4):05d}_m{round(muf * 1e4):05d}"
    old = REPO / "results/energy_host/models" / f"{sec}.lib"
    new = eh.MODELS / f"{sec}.lib"
    if old.exists() and not new.exists() and not (abs(vth - eh.VTH0) < 1e-9 and abs(muf - 1.0) < 1e-9):
        new.write_bytes(old.read_bytes())
    return _eh_corner(vth, muf)


eh.corner = _corner
for d in (RAW, SUMM):
    d.mkdir(parents=True, exist_ok=True)
VDD = 3.3

# ---------------------------------------------------------------- protocol constants (frozen in DECISIONS.md H2)
T1_BASE, WMIN, RESET_BASE, WINDOW_BASE = 170.0, 20.0, 300.0, 4000.0   # window = timeout bound (H1 outcome)
RSTB_REL = 50.0          # us, rstb (na precharge) release, not scaled
D_BASE, READ_BASE = 50.0, 10.0   # early end: rows off D after the first output edge; outputs read READ after that
K_MIN, K_MAX = 1.0, 2.5
SCALE_D = True           # D and READ scale with k (decided in H1 checks; see DECISIONS.md)
STOP_TAIL = 5.0          # us simulated after the read time (simulation setting only)
T_ON0 = 320.0            # us, trip counting start before the reset extension (score.py convention)


def levels(vhat):
    """build_A V_th-referenced levels from the host's |V_th| estimate, rounded to 1 mV."""
    return round(VDD - vhat - 0.83, 3), round(VDD - vhat - 0.25, 3)


def kfac(mu_hat):
    return float(min(max(1.0 / mu_hat, K_MIN), K_MAX))


def timing(k, scale_d=None, scale_reset=True):
    sd = SCALE_D if scale_d is None else scale_d
    return dict(k=k, T1=round(T1_BASE * k, 3), reset_ext=round(RESET_BASE * (k - 1), 3) if scale_reset else 0.0,
                window=round(WINDOW_BASE * k, 3),
                D=round(D_BASE * (k if sd else 1.0), 3), READ=round(READ_BASE * (k if sd else 1.0), 3))


def ic_line(state):
    return ".ic " + " ".join(f"v({n})={state[n]:.6f}" for n in state) + " v(vboot)=0"


def load_prior(tag):
    """.dat/.cols prior (common.save_prior format) -> {node: value} at its last row."""
    cols = pathlib.Path(str(tag) + ".cols").read_text().split()
    d = np.atleast_2d(np.loadtxt(str(tag) + ".dat"))
    return {n: float(d[-1, 2 * k + 1]) for k, n in enumerate(cols)}


def build_cls(dst, idx=None, x=None, vth=0.65, muf=1.0, mc=None, V1=None, V2=None, k=1.0, prior_state=None,
              inst=False, scale_d=None, rstb_rel=RSTB_REL, cold=True, warm_prior=None, adaptive=True, scale_reset=True):
    """Host protocol v2 classification netlist. prior_state: dict node->V for the power-up start (None = all 0 V).
    cold=False with warm_prior: v1-style warm start (VDD on), used only for v1 reference runs built through here."""
    tm = timing(k, scale_d, scale_reset)
    kw = dict(vth=vth, muf=muf, mc=mc, V1=V1, V2=V2, T1=tm["T1"], WMIN=WMIN, trace=tm["window"], reset_ext=tm["reset_ext"],
              inst=inst, cold=cold, x=x)
    if rstb_rel is not None:
        kw["rstb_rel"] = rstb_rel
    if warm_prior is not None:
        kw["prior"] = warm_prior
    b = eh.build(dst, idx, **kw)
    t = pathlib.Path(dst).read_text()
    ext = tm["reset_ext"]
    if adaptive:
        D = tm["D"]
        host = ["* ---- host model v2 (ideal, NOT part of the die): early race end ----",
                f"Bhflag hflag 0 V = ((time > {(T_ON0 + ext) * 1e-6:.4e}) && (max(max(max(v(na1), v(na2)), max(v(na3), v(na4))), v(na5)) > 1.65)) ? 1 : 0",
                "Ghint 0 htime hflag 0 1", "Chint htime 0 1", "Rhint htime 0 1e12"]
        for i in range(1, 7):
            t, n = re.subn(rf"^VR{i}\s+row{i}\s+0\s+", f"VR{i} rowpre{i} 0 ", t, flags=re.M); assert n == 1
            host.append(f"Brow{i} row{i} rowpre{i} V = (3.3 - v(rowpre{i})) * min(max((v(htime) - {D * 1e-6:.4e}) / 0.2e-6, 0), 1)")
        t, n = re.subn(r"^(VDD\s+vdd\s+0\s+.*)$", lambda m: m.group(1) + "\n" + "\n".join(host), t, count=1, flags=re.M); assert n == 1
    if prior_state is not None:
        t, n = re.subn(r"^\.ic .*$", ic_line(prior_state), t, flags=re.M); assert n == 1
    pathlib.Path(dst).write_text(t)
    b.update(tm)
    b["adaptive_D"] = tm["D"] if adaptive else None
    b["t_on_us"] = T_ON0 + ext
    b["stop_htime_us"] = tm["D"] + 0.2 + tm["READ"] + STOP_TAIL if adaptive else None
    return b


FALLBACK_OPTS = ".options NOOPITER"   # H4.1: retry with gmin stepping only if the first attempt produced no data


def simulate(net, tag, vecs, stop_htime_us=None, timeout=None, opts=C.RELAX, fallback=True):
    """Run once; if no data (solver stall/timeout), run again with FALLBACK_OPTS added (recorded in info)."""
    t1 = timeout if timeout is not None else 5400
    d, info = _simulate(net, tag, vecs, stop_htime_us, t1, opts)
    if d is None and fallback:
        d, info2 = _simulate(net, tag, vecs, stop_htime_us, 10800, FALLBACK_OPTS + "\n" + opts)
        info2["first_attempt"] = info
        info2["fallback"] = FALLBACK_OPTS
        info = info2
    return d, info


def _simulate(net, tag, vecs, stop_htime_us, timeout, opts):
    """eh.simulate with an optional early stop: the transient ends when v(htime) (s since the first output) exceeds
    stop_htime_us (ngspice 'stop when' breakpoint; the data up to that point are written)."""
    net = pathlib.Path(net)
    txt = re.sub(r"(?is)^\.control.*?^\.endc\s*$", "", net.read_text(), flags=re.M)
    ctl = [opts, ".control", "set filetype=binary"]
    if stop_htime_us is not None:
        ctl.append(f"stop when v(htime) > {stop_htime_us * 1e-6:.6e}")
    ctl += ["run", f"write {tag}.raw " + " ".join(vecs), "quit", ".endc"]
    i = txt.rstrip().rfind("\n.end")
    run = net.with_name(f"_{tag}.cir")
    run.write_text(txt[:i] + "\n" + "\n".join(ctl) + txt[i:])
    s = time.time()
    try:
        r = subprocess.run(["ngspice", "-b", run.name], cwd=run.parent, capture_output=True, text=True,
                           timeout=timeout, stdin=subprocess.DEVNULL)
        out = r.stdout + r.stderr
        rc = r.returncode
    except subprocess.TimeoutExpired:
        out, rc = "TIMEOUT", -9
    info = dict(wall_s=round(time.time() - s, 1), returncode=rc,
                warnings=[l.strip() for l in out.splitlines() if re.search(r"error|abort|singular|too small|failed", l, re.I)][:20])
    raw = run.with_name(f"{tag}.raw")
    if not raw.exists():
        info["error"] = "no data"
        run.with_name(f"{tag}.log").write_text(out[-5000:])
        return None, info
    d = eh.read_raw(raw)
    raw.unlink()
    run.unlink()
    return d, info


def metrics_v2(d, b, vth_metric):
    """common.metrics with the trip-counting start and the reset-level sample shifted by the reset extension, plus
    the host-observed outcome at the read time."""
    ext = b["reset_ext"]
    C.T_ON, C.T_RESET_SAMPLE = (T_ON0 + ext) * 1e-6, (311.0 + ext) * 1e-6
    try:
        t = d["time"]
        v = {n: d[f"v({n})"] for n in C.NODES}
        m = C.metrics(t, v, b["tC2"], vth=vth_metric)
    finally:
        C.T_ON, C.T_RESET_SAMPLE = 320e-6, 311e-6
    m["race_us"] = round(min(m["trip_us"].values()) - b["tC2"], 3) if m["trip_us"] else None
    t_last = float(t[-1]) * 1e6
    stopped = b.get("adaptive_D") is not None and t_last < b["t_end"] - 1.0   # stopped by the host timer
    if b.get("adaptive_D") is not None and m["trip_us"]:
        t_read = min(min(m["trip_us"].values()) + b["adaptive_D"] + 0.2 + b["READ"], t_last)
        if stopped and t_read - (t_last - STOP_TAIL) > 0.15:   # H4.2: timer started before the first trip
            t_read = t_last - STOP_TAIL                         # (exact to one time step, <= 0.1 us)
    elif stopped:
        t_read = t_last - STOP_TAIL
    else:
        t_read = t_last
    m["t_rows_off_us"] = round(t_read - 0.2 - b["READ"], 3) if b.get("adaptive_D") is not None else None
    m["host_timer_pre_trip_us"] = (round(b["adaptive_D"] - (m["t_rows_off_us"] - min(m["trip_us"].values())), 3)
                                   if (b.get("adaptive_D") is not None and m["trip_us"] and stopped) else None)
    lat = [kk for kk in range(1, 6) if np.interp(t_read * 1e-6, t, v[f"na{kk}"]) > 2.5]
    m["t_read_us"] = round(t_read, 3)
    m["latched_read"] = lat
    m["na_read"] = {kk: round(float(np.interp(t_read * 1e-6, t, v[f"na{kk}"])), 4) for kk in range(1, 6)}
    first = m["first"]
    if not m["trip_us"]:
        f = "stuck_latched" if lat else "timeout"
    elif not lat:
        f = "none_latched"
    elif len(lat) > 1:
        f = "multi_latched"
        if m.get("lock_us") and any(m["trip_us"][kk] > m["lock_us"] for kk in lat if kk in m["trip_us"]):
            f = "lockout_failed"
    elif lat[0] != first:
        f = "latched_not_first"
    else:
        f = None
    m["valid_read"] = f is None
    m["failure_read"] = f
    m["winner_read"] = lat[0] if f is None else None
    m["trip_in_C1"] = bool(m["trip_us"] and min(m["trip_us"].values()) < b["tC2"])
    return m, t_read


def vecs(ammeters=()):
    v = [f"v({n})" for n in C.NODES + [f"row{i}" for i in range(1, 7)] + ["vdd", "htime"]]
    if ammeters:
        v += [f"i({s})" for s in eh.SOURCES] + [f"i(VAM_{p}_{bb})" for p, bb in ammeters]
    return v


STATE_NODES = C.WARM_NODES + ["n1", "comp", "acom"] + [f"acol{k}" for k in range(1, 6)]


def state_at(d, t_s, nodes=STATE_NODES):
    return {n: float(np.interp(t_s, d["time"], d[f"v({n})"])) for n in nodes if f"v({n})" in d}


def run_cls(job):
    """job: tag, outdir, idx | x, vth, muf, mc, V1, V2, k, prior_state | prior_json(+key), inst, save_wave, vth_metric,
    scale_d, rstb_rel, cold, warm_prior, adaptive. Writes <tag>.json (+ .csv.gz, .cir.gz)."""
    outdir = pathlib.Path(job["outdir"])
    outdir.mkdir(parents=True, exist_ok=True)
    f = outdir / f"{job['tag']}.json"
    if f.exists():
        return json.load(open(f))
    wd = C.workdir(f'hv2_{job.get("wdir", "runs")}')
    net = wd / f"{job['tag']}.cir"
    ps = job.get("prior_state")
    if ps is None and job.get("prior_json"):
        ps = json.load(open(job["prior_json"]))[job.get("prior_key", "state")]
    bk = {kk: job[kk] for kk in ("x", "vth", "muf", "mc", "V1", "V2", "k", "inst", "scale_d", "rstb_rel", "cold",
                                 "warm_prior", "adaptive", "scale_reset") if kk in job}
    b = build_cls(net, job.get("idx"), prior_state=ps, **bk)
    if "warm_prior" in bk:
        bk["warm_prior"] = str(bk["warm_prior"])
    d, info = simulate(net, job["tag"], vecs(b["ammeters"]), stop_htime_us=b["stop_htime_us"])
    idx = job.get("idx")
    label = job["label"] if "label" in job else (int(C.YTE[idx]) + 1 if idx is not None else None)
    meta = dict(tag=job["tag"], idx=idx, label=label,
                job={kk: (str(vv) if isinstance(vv, pathlib.PurePath) else vv) for kk, vv in job.items()
                     if kk not in ("outdir", "x", "prior_state")},
                prior_state=ps, run=info, build={kk: vv for kk, vv in b.items() if kk not in ("draws", "ammeters")})
    if d is not None:
        m, t_read = metrics_v2(d, b, job.get("vth_metric", job.get("vth", 0.65)))
        meta.update(m)
        meta["end_state_read"] = state_at(d, t_read * 1e-6)
        if b["ammeters"]:
            meta["energy"] = eh.energy(d, dict(b, t_end=t_read), m["lock_us"])
        if job.get("save_wave", True):
            tt = d["time"]
            tb = np.arange(0, tt[-1] + 1e-12, 1e-6)
            cols = [tb * 1e6] + [np.interp(tb, tt, d[f"v({n})"]) for n in C.NODES + ["row1"]]
            with gzip.open(outdir / f"{job['tag']}.csv.gz", "wt") as g:
                g.write("t_us," + ",".join(C.NODES + ["row1"]) + "\n")
                np.savetxt(g, np.column_stack(cols), fmt="%.5g", delimiter=",")
    f.write_text(json.dumps(meta, indent=1, default=float))
    with open(net) as a, gzip.open(outdir / f"{job['tag']}.cir.gz", "wt") as g:
        g.write(a.read())
    if b.get("draws"):
        (outdir / f"{job['tag']}_draws.json").write_text(json.dumps(b["draws"]))
    net.unlink()
    return meta


# ---------------------------------------------------------------- VDD-off period (power gating)
def run_off(tag, outdir, state, T_off_s, vth=0.65, muf=1.0, mc=None, probe_s=(1e-3, 1e-2, 1e-1, 1.0, 10.0)):
    """VDD-off period after a classification: from the read-time state (rows already back at 3.3 V, rstr/rstb/phib
    at 3.3 V, phi 0 V) every source ramps to 0 V over 10 us (from 1 us) and stays there for T_off_s. Free timestep.
    Returns the end state (the next power-up's start state) and node values at the probe times."""
    outdir = pathlib.Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    f = outdir / f"{tag}.json"
    if f.exists():
        return json.load(open(f))
    wd = C.workdir("hv2_off")
    net = wd / f"{tag}.cir"
    eh.build(net, 0, vth=vth, muf=muf, mc=mc, inst=False)
    t = net.read_text()
    dn = "PWL(0 3.3 1u 3.3 11u 0)"
    t, n = re.subn(r"^VDD\s+vdd\s+0\s+.*$", f"VDD vdd 0 {dn}", t, flags=re.M); assert n == 1
    for i in range(1, 7):
        t, n = re.subn(rf"^(VR{i}\s+row{i}\s+0\s+).*$", rf"\g<1>{dn}", t, flags=re.M); assert n == 1
    for nm, node in (("V_RSTR", "rstr"), ("V_RSTB", "rstb"), ("V_PHIB", "phib")):
        t, n = re.subn(rf"^{nm}\s.*$", f"{nm} {node} 0 {dn}", t, flags=re.M); assert n == 1
    t, n = re.subn(r"^V_PHI\s.*$", "V_PHI phi 0 DC 0", t, flags=re.M); assert n == 1
    t, n = re.subn(r"^\.ic .*$", ic_line(state), t, flags=re.M); assert n == 1
    t, n = re.subn(r"^\.tran .*$", f".tran 1u {T_off_s:g} 0 {max(T_off_s / 400, 1e-6):g}", t, flags=re.M); assert n == 1
    net.write_text(t)
    d, info = simulate(net, tag, [f"v({x})" for x in STATE_NODES] + ["v(vdd)"], timeout=60)
    rec = dict(tag=tag, T_off_s=T_off_s, vth=vth, muf=muf, mc=mc, start_state=state, run=info)
    if d is not None:
        rec["end_state"] = state_at(d, d["time"][-1])
        rec["probe"] = {f"{p:g}": state_at(d, p) for p in probe_s if p <= d["time"][-1] * 1.0001}
    f.write_text(json.dumps(rec, indent=1, default=float))
    net.unlink()
    return rec


def pool_run(fn, jobs, nproc=4):
    from multiprocessing import Pool
    seen = set()
    jobs = [j for j in jobs if not (pathlib.Path(j["outdir"]) / f"{j['tag']}.json").exists()
            and not (j["tag"] in seen or seen.add(j["tag"]))]
    s = time.time()
    with Pool(nproc) as p:
        for kk, m in enumerate(p.imap_unordered(fn, jobs), 1):
            print(f"[{kk}/{len(jobs)} {time.time()-s:6.0f}s] {m['tag']} label {m.get('label')} read {m.get('latched_read')} "
                  f"{m.get('failure_read')} race {m.get('race_us')} t_read {m.get('t_read_us')} wall {m['run']['wall_s']}", flush=True)


# ---------------------------------------------------------------- calibration: supply-current method (a1, v2 sequence)
A1_I = (5e-6, 20e-6, 45e-6)      # A, pass-1 target currents (energy/host study a1)
A1_RAMP = (300.0, 4300.0, 1.3)   # ramp start, end (us), final row level (V)
A1_PHIB_OFF = 290.0
A1_MAXSTEP_US = 0.1              # simulation max step during the a1 transient


def three_point(V, I):
    """sqrt(I) = a*(V - Vth - R*I): exact solve -> (a, Vth, R)."""
    V, I = np.asarray(V, float), np.asarray(I, float)
    a, aV, aR = np.linalg.solve(np.column_stack([V, -np.ones(3), -I]), np.sqrt(I))
    return float(a), float(aV / a), float(aR / a)


def vsg_at(vsg, di, I):
    k = np.where(di >= I)[0]
    if not len(k) or k[0] == 0:
        return None
    k = k[0]
    return float(np.interp(I, [di[k - 1], di[k]], [vsg[k - 1], vsg[k]]))


def a1_extract(vsg, di, a_nom=None):
    """Two-pass extraction (DECISIONS H2): pass 1 at A1_I -> a1; mu1 = (a1/a_nom)^2; pass 2 at mu1*A1_I -> (a, Vth_raw).
    a_nom None (nominal calibration): pass 2 = pass 1 currents."""
    p1 = [vsg_at(vsg, di, I) for I in A1_I]
    if None in p1:
        return None
    a1, v1, r1 = three_point(p1, A1_I)
    mu1 = (a1 / a_nom) ** 2 if a_nom else 1.0
    I2 = [mu1 * I for I in A1_I]
    p2 = [vsg_at(vsg, di, I) for I in I2]
    if None in p2:
        return None
    a2, v2, r2 = three_point(p2, I2)
    return dict(pass1=dict(vsg=p1, a=a1, vth=v1, R=r1, mu=mu1), pass2=dict(I=I2, vsg=p2, a=a2, vth=v2, R=r2),
                a=a2, vth_raw=v2)


def run_a1(tag, outdir, vth=0.65, muf=1.0, mc=None, prior_state=None, maxstep_us=A1_MAXSTEP_US, cold=True, precharge=None,
           ramp=None):
    """a1 under the v2 power-up: VDD/rows/phi ramp 0 -> level over 0-10 us (from prior_state, None = all 0 V), rstr low
    from t = 0, rstb released at RSTB_REL, phib low until 290 us, rows ramp 3.3 -> 1.3 V over 300-4300 us. Host records
    I_DD (supply-current meter) and its own row level; baseline = mean I_DD over 293-300 us."""
    outdir = pathlib.Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    f = outdir / f"{tag}.json"
    if f.exists():
        return json.load(open(f))
    wd = C.workdir("hv2_a1")
    net = wd / f"{tag}.cir"
    eh.build(net, 0, vth=vth, muf=muf, mc=mc, inst=False, cold=cold, rstb_rel=RSTB_REL)
    t = net.read_text()
    t0, t1, vend = A1_RAMP if ramp is None else ramp
    pre = "0 0 10u 3.3" if cold else "0 3.3"
    if precharge:   # rail precharge pulse (rows at level pl from pa to pb us, 1 us edges)
        pa, pb, pl = precharge
        pre += f" {pa}u 3.3 {pa+1}u {pl} {pb}u {pl} {pb+1}u 3.3"
    for i in range(1, 7):
        t, n = re.subn(rf"^(VR{i}\s+row{i}\s+0\s+).*$", rf"\g<1>PWL({pre} {t0}u 3.3 {t1}u {vend} {t1+1}u 3.3)", t, flags=re.M); assert n == 1
    rend = f" {t1+2}u 0 {t1+3}u 3.3"   # rstr back high after the ramp (idle level before VDD goes off)
    t, n = re.subn(r"^V_RSTR\s.*$", f"V_RSTR rstr 0 PWL(0 0{rend})" if cold else f"V_RSTR rstr 0 PWL(0 3.3 20u 0{rend})", t, flags=re.M); assert n == 1
    t, n = re.subn(r"^V_PHIB\s.*$", f"V_PHIB phib 0 PWL(0 0 {A1_PHIB_OFF}u 0 {A1_PHIB_OFF+1}u 3.3)", t, flags=re.M); assert n == 1
    t, n = re.subn(r"^V_PHI\s.*$", f"V_PHI phi 0 PWL({pre} {A1_PHIB_OFF}u 3.3 {A1_PHIB_OFF+1}u 0)", t, flags=re.M); assert n == 1
    t, n = re.subn(r"^\.tran .*$", f".tran 100n {t1+20:.0f}u 0 {maxstep_us:g}u", t, flags=re.M); assert n == 1
    if prior_state is not None:
        t, n = re.subn(r"^\.ic .*$", ic_line(prior_state), t, flags=re.M); assert n == 1
    net.write_text(t)
    vv = ["v(row1)", "i(vdd)", "v(vdd)"] + [f"v({x})" for x in STATE_NODES]
    d, info = simulate(net, tag, vv, timeout=1800)
    rec = dict(tag=tag, vth=vth, muf=muf, mc=mc, prior_state=prior_state, maxstep_us=maxstep_us, cold=cold, run=info,
               precharge=precharge, ramp=(t0, t1, vend))
    if d is not None:
        tt = d["time"]
        idd = -d["i(vdd)"]
        base = float(np.mean(idd[(tt > 293e-6) & (tt < 300e-6)]))
        m = (tt > t0 * 1e-6) & (tt <= t1 * 1e-6)
        vsg = 3.3 - d["v(row1)"][m]
        di = idd[m] - base
        g = np.linspace(t0 * 1e-6, t1 * 1e-6, 2001)
        rec.update(I_base_uA=base * 1e6, curve=dict(vsg=list(np.interp(g, tt[m], vsg)), dI_uA=list(np.interp(g, tt[m], di) * 1e6)),
                   ext_nominal=a1_extract(vsg, di), na_max_ramp=float(max(np.max(d[f"v(na{k})"][m]) for k in range(1, 6))),
                   ap_max=float(max(np.max(d[f"v(ap{k})"]) for k in range(1, 6))),
                   E_VDD_nJ=float(np.trapezoid(idd * d["v(vdd)"], tt)) * 1e9,
                   ap_at_ramp=[float(np.interp(t0 * 1e-6, tt, d[f"v(ap{k})"])) for k in range(1, 6)],
                   ap_end=[float(d[f"v(ap{k})"][-1]) for k in range(1, 6)],
                   ref_at_ramp=float(np.interp(t0 * 1e-6, tt, d["v(ref)"])), ref_end=float(d["v(ref)"][-1]),
                   end_state=state_at(d, tt[-1]))
    f.write_text(json.dumps(rec, indent=1, default=float))
    net.unlink()
    return rec


# ---------------------------------------------------------------- calibration session (DECISIONS H2 §1)
MU_OV = 0.6            # V: mu estimate = dI_DD at V_SG = Vraw + MU_OV, relative to the nominal die
RACE_OV = (0.45, 0.30) # race-timing cross-check: V2 = 3.3 - Vhat - ov (x = 0 races)
FLAG_MV = 50.0         # cross-check: |Vrace - Vhat| above this flags the calibration
T_OFF_S = 1.0          # VDD-off time between steps and between classifications
CAL = RAW / "cal"
DESIGN_F = SUMM / "design_constants.json"


def a1_estimates(rec, design=None):
    """(Vraw, dI at Vraw+MU_OV) from an a1 record; with design constants also (Vhat, mu_hat)."""
    v, di = np.array(rec["curve"]["vsg"]), np.array(rec["curve"]["dI_uA"]) * 1e-6
    e = a1_extract(v, di)
    if e is None:
        return None
    vraw = e["pass1"]["vth"]
    i_ov = float(np.interp(vraw + MU_OV, v, di)) if vraw + MU_OV <= v.max() else None
    out = dict(vraw=vraw, a_pass1=e["pass1"]["a"], i_ov_uA=i_ov * 1e6 if i_ov else None, vsg=e["pass1"]["vsg"])
    if design:
        out["vhat"] = vraw - design["a1_offset_V"]
        out["mu_hat"] = (i_ov * 1e6 / design["I_ref_uA"]) if i_ov else None
    return out


def race_vth(t_a, t_b, V2s):
    if not t_a or not t_b or t_a <= 0 or t_b <= 0:
        return None
    r = np.sqrt(t_b / t_a)
    A, B = 3.3 - V2s[0], 3.3 - V2s[1]
    return float((r * B - A) / (r - 1))


def off_state(tag, outdir, state, vth, muf, mc):
    return run_off(tag, outdir, state, T_OFF_S, vth=vth, muf=muf, mc=mc, probe_s=(1e-3, T_OFF_S))["end_state"]


def calibrate(key, vth=0.65, muf=1.0, mc=None, design=None, nominal=False):
    """Host calibration session on one die/condition. Sequence (H2 §1): long VDD-off (all 0 V) -> a1 -> 1 s off ->
    race a (x = 0) -> 1 s off -> race b (x = 0) -> 1 s off -> start state for the classifications.
    nominal=True: the design-time run on the nominal die (levels from the true 0.65 V, k = 1, no flag)."""
    out = CAL / key
    f = out / "calibration.json"
    if f.exists():
        return json.load(open(f))
    a1 = run_a1(f"{key}_a1", out, vth=vth, muf=muf, mc=mc, maxstep_us=1.0)
    est = a1_estimates(a1, None if nominal else design)
    if not nominal and (est is None or est.get("mu_hat") is None):   # H2.1 step 2: calibration fails
        rec = dict(key=key, vth=vth, muf=muf, mc=mc, a1=est, failed=True, flag=True)
        f.write_text(json.dumps(rec, indent=1, default=float))
        return rec
    if nominal:
        vhat, mu_hat = 0.65, 1.0
    else:
        vhat, mu_hat = est["vhat"], est["mu_hat"]
    k = kfac(mu_hat)
    V1 = levels(vhat)[0]
    V2s = tuple(round(3.3 - vhat - ov, 3) for ov in RACE_OV)
    st = off_state(f"{key}_off_a1", out, _a1_end_state(a1), vth, muf, mc)
    races = []
    for j, V2 in enumerate(V2s):
        m = run_cls(dict(tag=f"{key}_race{'ab'[j]}", outdir=out, wdir="cal", idx=None, x=np.zeros(6), label=None,
                         vth=vth, muf=muf, mc=mc, V1=V1, V2=V2, k=k, prior_state=st, save_wave=False, vth_metric=vth))
        races.append(m)
        st = off_state(f"{key}_off_race{'ab'[j]}", out, m["end_state_read"], vth, muf, mc)
    vr = race_vth(races[0].get("race_us"), races[1].get("race_us"), V2s)
    rec = dict(key=key, vth=vth, muf=muf, mc=mc, a1=est, vhat=vhat, mu_hat=mu_hat, k=k, levels=levels(vhat),
               race=dict(V2s=V2s, t_us=[r.get("race_us") for r in races], vraw=vr), start_state=st)
    if not nominal:
        rec["race"]["vhat_race"] = (vr - design["race_offset_V"]) if vr is not None else None
        rec["flag"] = (vr is None) or abs(rec["race"]["vhat_race"] - vhat) * 1e3 > FLAG_MV
        rec["err_mV"] = dict(a1=(vhat - vth) * 1e3, race=(rec["race"]["vhat_race"] - vth) * 1e3 if vr is not None else None)
        rec["mu_err_rel"] = mu_hat / muf - 1 if mu_hat else None
    f.write_text(json.dumps(rec, indent=1, default=float))
    return rec


def _a1_end_state(a1):
    return a1["end_state"]
