"""Host protocol v2.1 tooling (results/host_v21). Imports host_v2/scripts/hv2.py (and through it energy_host and the
fitc10 campaign tooling) read-only; nothing in an earlier folder is written.

Circuit: Variant 3 at fitc10, weights rev10/eval/F_hw_m4_firstpass.npy (unchanged). Only the host protocol changes.
Every rule and constant is defined in DECISIONS.md (P-sections).

v2.1 = v2 (host_v2 DECISIONS H2 + H4) plus adaptive power gating (DECISIONS P2):
  mode "G" (gated): exactly v2. VDD and every line off for T_off = 1 s between classifications; cold power-up.
  mode "W" (VDD on): VDD stays on between classifications (idle levels, 1 s), every classification starts warm from
    the state the idle leaves; rstb released at 50 us (the energy/host study's v1 rstb fix, E11.1). Levels, k, early end and
    timeout as v2.
The mode is chosen once per calibration session from the a1 estimate: W if V_hat < V_GATE, else G.

Extra here (measurement only, no electrical change): the 11 source currents are saved in every classification and
idle run, so energy per classification and standby energy are computed for every run.
"""
import gzip, json, pathlib, re, shutil, sys
import numpy as np

HV21 = pathlib.Path(__file__).resolve().parents[1]
REPO = HV21.parents[1]
HV2 = REPO / "results/host_v2"
sys.path.insert(0, str(HV2 / "scripts"))
import hv2           # noqa: E402  (read-only)
import eh            # noqa: E402
import common as C   # noqa: E402

RAW, SUMM = HV21 / "raw", HV21 / "summary"
CAL = RAW / "cal"
for d in (RAW, SUMM, CAL):
    d.mkdir(parents=True, exist_ok=True)

# Corner .lib files live in host_v21/models; existing ones are copied byte-identically from host_v2 (or energy_host).
eh.MODELS = HV21 / "models"
eh.MODELS.mkdir(exist_ok=True)


def _corner(vth=eh.VTH0, muf=1.0):
    sec = f"eh_v{round(vth * 1e4):05d}_m{round(muf * 1e4):05d}"
    new = eh.MODELS / f"{sec}.lib"
    if not new.exists() and not (abs(vth - eh.VTH0) < 1e-9 and abs(muf - 1.0) < 1e-9):
        for src in (HV2 / "models", REPO / "results/energy_host/models"):
            if (src / f"{sec}.lib").exists():
                shutil.copyfile(src / f"{sec}.lib", new)
                break
    return hv2._eh_corner(vth, muf)


eh.corner = _corner

# ---------------------------------------------------------------- v2.1 constants (frozen in DECISIONS.md P2)
V_GATE = 0.600           # V: mode W (VDD on) if the a1 estimate V_hat < V_GATE, else mode G (full v2)
RSTB_REL_W = 50.0        # us, rstb release in mode W (energy/host study E11.1 fix); mode G uses v2's 50 us as well
T_IDLE_S = 1.0           # s between classifications in both modes (G: VDD off; W: VDD on at idle levels)
DESIGN_V2 = json.load(open(HV2 / "summary/design_constants.json"))   # c_a1, I_ref, c_race (mode G), read-only
DESIGN_W_F = SUMM / "design_constants_W.json"                         # c_race for mode W (nominal die)
SRC_VECS = [f"i({s})" for s in eh.SOURCES]


def mode_of(vhat):
    return "W" if vhat < V_GATE else "G"


# ---------------------------------------------------------------- energy (energy/host study E1 'net', from the source currents)
def source_energy(d, t0_s, t1_s):
    t = d["time"]
    out = {}
    for s, node in eh.SOURCES.items():
        p = d[f"v({node})"] * (-d[f"i({s.lower()})"])
        out[s] = eh._integ(t, p, t0_s, t1_s)
    out["total"] = sum(out.values())
    return out


# ---------------------------------------------------------------- classification (both modes)
def run_cls(job):
    """job: tag, outdir, idx | x(+label), vth, muf, mc, V1, V2, k, mode ('G'|'W'), prior_state, vth_metric, ramp_us.
    Mode G = hv2 classification (cold power-up from prior_state). Mode W = warm start (VDD on) from prior_state,
    rstb released at RSTB_REL_W. Writes <tag>.json, .csv.gz (1 us waveforms), .cir.gz."""
    outdir = pathlib.Path(job["outdir"])
    outdir.mkdir(parents=True, exist_ok=True)
    f = outdir / f"{job['tag']}.json"
    if f.exists():
        return json.load(open(f))
    wd = C.workdir(f'hv21_{job.get("wdir", "runs")}')
    net = wd / f"{job['tag']}.cir"
    mode = job["mode"]
    x = job.get("x")
    b = hv2.build_cls(net, job.get("idx"), x=x, vth=job["vth"], muf=job["muf"], mc=job.get("mc"), V1=job["V1"],
                      V2=job["V2"], k=job["k"], prior_state=job["prior_state"],
                      cold=(mode == "G"), rstb_rel=hv2.RSTB_REL if mode == "G" else RSTB_REL_W)
    if mode == "G" and job.get("ramp_us", 10.0) != 10.0:
        set_powerup_ramp(net, job["ramp_us"])
    d, info = hv2.simulate(net, job["tag"], hv2.vecs() + SRC_VECS, stop_htime_us=b["stop_htime_us"])
    idx = job.get("idx")
    label = job["label"] if "label" in job else (int(C.YTE[idx]) + 1 if idx is not None else None)
    meta = dict(tag=job["tag"], idx=idx, label=label, mode=mode,
                job={kk: (str(vv) if isinstance(vv, pathlib.PurePath) else vv) for kk, vv in job.items()
                     if kk not in ("outdir", "x", "prior_state")},
                prior_state=job["prior_state"], run=info, build={kk: vv for kk, vv in b.items() if kk not in ("draws", "ammeters")})
    if d is not None:
        m, t_read = hv2.metrics_v2(d, b, job.get("vth_metric", job["vth"]))
        meta.update(m)
        meta["end_state_read"] = hv2.state_at(d, t_read * 1e-6)
        meta["energy_nJ"] = {s: e * 1e9 for s, e in source_energy(d, 0.0, t_read * 1e-6).items()}
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
    net.unlink()
    return meta


def set_powerup_ramp(net, ramp_us):
    """Mode-G power-up: VDD, the six rows and phi ramp 0 -> level over 0-ramp_us instead of 0-10 us (P4 ramp stress)."""
    t = pathlib.Path(net).read_text()
    t, n = re.subn(r"PWL\(0 0 10u 3\.3", f"PWL(0 0 {ramp_us:.4g}u 3.3", t)
    assert n == 8, n
    pathlib.Path(net).write_text(t)


# ---------------------------------------------------------------- idle between classifications
def run_idle(tag, outdir, state, mode, vth=0.65, muf=1.0, mc=None, T_s=T_IDLE_S, ramp_us=10.0):
    """Idle period after a read (or after a1). mode G: hv2.run_off semantics (every source ramps to 0 V over ramp_us
    from 1 us, then 0 V). mode W: VDD 3.3 V and every line at its idle level (rows/rstr/rstb/phib 3.3 V, phi 0 V; energy/host
    study E2 levels) for T_s. Free time step (max T_s/400). Source currents saved: idle energy and power at probe times."""
    outdir = pathlib.Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    f = outdir / f"{tag}.json"
    if f.exists():
        return json.load(open(f))
    wd = C.workdir("hv21_idle")
    net = wd / f"{tag}.cir"
    eh.build(net, 0, vth=vth, muf=muf, mc=mc, inst=False)
    t = net.read_text()
    if mode == "G":
        dn = f"PWL(0 3.3 1u 3.3 {1 + ramp_us:.4g}u 0)"
        lev = dict(VDD=dn, rows=dn, V_RSTR=dn, V_RSTB=dn, V_PHIB=dn, V_PHI="DC 0")
    else:
        lev = dict(VDD="DC 3.3", rows="DC 3.3", V_RSTR="DC 3.3", V_RSTB="DC 3.3", V_PHIB="DC 3.3", V_PHI="DC 0")
    t, n = re.subn(r"^VDD\s+vdd\s+0\s+.*$", f"VDD vdd 0 {lev['VDD']}", t, flags=re.M); assert n == 1
    for i in range(1, 7):
        t, n = re.subn(rf"^(VR{i}\s+row{i}\s+0\s+).*$", rf"\g<1>{lev['rows']}", t, flags=re.M); assert n == 1
    for nm, node in (("V_RSTR", "rstr"), ("V_RSTB", "rstb"), ("V_PHIB", "phib"), ("V_PHI", "phi")):
        t, n = re.subn(rf"^{nm}\s.*$", f"{nm} {node} 0 {lev[nm]}", t, flags=re.M); assert n == 1
    t, n = re.subn(r"^\.ic .*$", hv2.ic_line(state), t, flags=re.M); assert n == 1
    t, n = re.subn(r"^\.tran .*$", f".tran 1u {T_s:g} 0 {max(T_s / 400, 1e-6):g}", t, flags=re.M); assert n == 1
    net.write_text(t)
    lines = [f"row{i}" for i in range(1, 7)] + C.TIMING
    d, info = hv2.simulate(net, tag, [f"v({x})" for x in hv2.STATE_NODES + lines] + ["v(vdd)"] + SRC_VECS, timeout=120)
    rec = dict(tag=tag, mode=mode, T_s=T_s, vth=vth, muf=muf, mc=mc, ramp_us=ramp_us, start_state=state, run=info)
    if d is not None:
        tt = d["time"]
        rec["end_state"] = hv2.state_at(d, tt[-1])
        e = source_energy(d, 0.0, tt[-1])
        rec["E_idle_nJ"] = {s: v * 1e9 for s, v in e.items()}
        ptot = sum(d[f"v({node})"] * (-d[f"i({s.lower()})"]) for s, node in eh.SOURCES.items())
        rec["P_uW_at"] = {f"{p:g}": float(np.interp(p, tt, ptot)) * 1e6 for p in (1e-4, 1e-3, 1e-2, 0.1, 0.5, T_s) if p <= tt[-1] * 1.0001}
        rec["P_mean_uW"] = e["total"] / tt[-1] * 1e6
        rec["probe"] = {f"{p:g}": hv2.state_at(d, p) for p in (1e-3, T_s) if p <= tt[-1] * 1.0001}
    f.write_text(json.dumps(rec, indent=1, default=float))
    net.unlink()
    return rec


def idle_state(tag, outdir, state, mode, vth, muf, mc):
    r = run_idle(tag, outdir, state, mode, vth=vth, muf=muf, mc=mc)
    if "end_state" not in r:
        raise RuntimeError(f"idle {tag} produced no data")
    return r["end_state"]


# ---------------------------------------------------------------- calibration session (DECISIONS P2.1)
def calibrate(key, vth=0.65, muf=1.0, mc=None, force_mode=None, nominal=False):
    """v2.1 calibration session: long off (all 0 V) -> a1 (v2 sequence, cold) -> mode decision -> idle (G: 1 s off;
    W: 1 s VDD on) -> race a -> idle -> race b -> idle -> start state of the first classification.
    force_mode: 'G'|'W' overrides the decision (labelled 'forced'; not the v2.1 policy).
    nominal=True: design-time run on the nominal die (V_hat = 0.65 V, mu_hat = 1 by definition, no flag)."""
    out = CAL / key
    f = out / "calibration.json"
    if f.exists():
        return json.load(open(f))
    a1 = hv2.run_a1(f"{key}_a1", out, vth=vth, muf=muf, mc=mc, maxstep_us=1.0)
    est = hv2.a1_estimates(a1, None if nominal else DESIGN_V2)
    if not nominal and (est is None or est.get("mu_hat") is None):   # v2 H2.1 step 2: calibration fails
        rec = dict(key=key, vth=vth, muf=muf, mc=mc, a1=est, failed=True, flag=True, mode=None)
        f.write_text(json.dumps(rec, indent=1, default=float))
        return rec
    vhat, mu_hat = (0.65, 1.0) if nominal else (est["vhat"], est["mu_hat"])
    mode = force_mode or mode_of(vhat)
    k = hv2.kfac(mu_hat)
    V1 = hv2.levels(vhat)[0]
    V2s = tuple(round(3.3 - vhat - ov, 3) for ov in hv2.RACE_OV)
    st = idle_state(f"{key}_idle_a1", out, a1["end_state"], mode, vth, muf, mc)
    races = []
    for j, V2 in enumerate(V2s):
        m = run_cls(dict(tag=f"{key}_race{'ab'[j]}", outdir=out, wdir="cal", idx=None, x=np.zeros(6), label=None,
                         vth=vth, muf=muf, mc=mc, V1=V1, V2=V2, k=k, mode=mode, prior_state=st, save_wave=False,
                         vth_metric=vth))
        races.append(m)
        st = idle_state(f"{key}_idle_race{'ab'[j]}", out, m["end_state_read"], mode, vth, muf, mc)
    vr = hv2.race_vth(races[0].get("race_us"), races[1].get("race_us"), V2s)
    rec = dict(key=key, vth=vth, muf=muf, mc=mc, a1=est, vhat=vhat, mu_hat=mu_hat, k=k, levels=hv2.levels(vhat),
               mode=mode, mode_forced=force_mode is not None, V_GATE=V_GATE,
               race=dict(V2s=V2s, t_us=[r.get("race_us") for r in races], vraw=vr), start_state=st)
    if not nominal:
        c_race = DESIGN_V2["race_offset_V"] if mode == "G" else json.load(open(DESIGN_W_F))["race_offset_V"]
        rec["race"]["c_race_V"] = c_race
        rec["race"]["vhat_race"] = (vr - c_race) if vr is not None else None
        rec["flag"] = (vr is None) or abs(rec["race"]["vhat_race"] - vhat) * 1e3 > hv2.FLAG_MV
        rec["err_mV"] = dict(a1=(vhat - vth) * 1e3, race=(rec["race"]["vhat_race"] - vth) * 1e3 if vr is not None else None)
        rec["mu_err_rel"] = mu_hat / muf - 1 if mu_hat else None
    f.write_text(json.dumps(rec, indent=1, default=float))
    return rec


def design_W():
    """Design-time constant for mode W: the race cross-check offset c_race_W from the nominal die (0.65 V, mu x1)
    run through the mode-W calibration sequence (P2.1). c_a1 and I_ref are v2's (a1 is unchanged)."""
    if DESIGN_W_F.exists():
        return json.load(open(DESIGN_W_F))
    rec = calibrate("design_nominal_W", 0.65, 1.0, None, force_mode="W", nominal=True)
    d = dict(race_offset_V=rec["race"]["vraw"] - 0.65, source="raw/cal/design_nominal_W (nominal die, mode W forced)",
             race=rec["race"], a1=rec["a1"])
    json.dump(d, open(DESIGN_W_F, "w"), indent=1, default=float)
    return d


def pool_run(fn, jobs, nproc=4):
    from multiprocessing import Pool
    import time
    seen = set()
    jobs = [j for j in jobs if not (pathlib.Path(j["outdir"]) / f"{j['tag']}.json").exists()
            and not (j["tag"] in seen or seen.add(j["tag"]))]
    s = time.time()
    with Pool(nproc) as p:
        for kk, m in enumerate(p.imap_unordered(fn, jobs), 1):
            print(f"[{kk}/{len(jobs)} {time.time()-s:6.0f}s] {m['tag']} mode {m.get('mode')} label {m.get('label')} "
                  f"read {m.get('latched_read')} {m.get('failure_read')} race {m.get('race_us')} t_read {m.get('t_read_us')} "
                  f"wall {m['run']['wall_s']}", flush=True)
