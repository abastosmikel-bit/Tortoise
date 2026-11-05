"""Shared tooling for the energy/host campaign (results/energy_host). Imports the fitc10 campaign tooling read-only.

Circuit: Variant 3 at fitc10 (fitc10_campaign DECISIONS D9/D11), current weights rev10/eval/F_hw_m4_firstpass.npy.
build() reproduces common.build(variant=3) byte for byte when no host option is set (checked by check_build.py), and
adds HOST-SIDE options only: row levels V1/V2, T1/WMIN, calibration duration, an early row-off time, the race window,
and arbitrary global corners (|V_th|, mobility factor). Circuit additions (the replica TFT) live in replica.py.

Instrumentation (instrument=True): every supply/host net that feeds more than one block is split per block through
0 V voltage sources (ammeters). Electrically identical; checked against the Phase 1 outcomes (check_instrument.py).
Energy: E = integral of v(source node) * i_out over the native ngspice time points (trapezoid), per source, per
block and per protocol phase.
"""
import gzip, json, os, pathlib, re, subprocess, sys, time
import numpy as np

os.environ["FC10_VARIANT"] = "3"
EH = pathlib.Path(__file__).resolve().parents[1]
REPO = EH.parents[1]
sys.path.insert(0, str(REPO / "results/fitc10_campaign/scripts"))
import common as C   # noqa: E402  (fitc10 campaign tooling, read-only)
import build_A       # noqa: E402  (frozen base-design builder, via common's sys.path)
assert C.VAR == 3

RAW, SUMM, MODELS = EH / "raw", EH / "summary", EH / "models"
for d in (RAW, SUMM, MODELS):
    d.mkdir(parents=True, exist_ok=True)
WARM = C.RAW / "warmstart/fitc10_warm"            # Variant 3 fitc10 warm start (end state, class 5 won)
SUB = json.load(open(C.CAMP / "summary/phase3_subset.json"))["subset"]   # the 20-sample subset
VDD = 3.3
MU0, VTH0 = 5.87, 0.65
SOURCES = {"VDD": "vdd", **{f"VR{i}": f"row{i}" for i in range(1, 7)},
           "V_RSTR": "rstr", "V_RSTB": "rstb", "V_PHIB": "phib", "V_PHI": "phi"}
HOST_LINES = [f"row{i}" for i in range(1, 7)] + ["rstr", "rstb", "phib", "phi"]


def formula_levels(vth):
    """build_A's V_th-referenced host levels."""
    return round(VDD - vth - 0.83, 4), round(VDD - vth - 0.25, 4)


# ----------------------------------------------------------------------------- corners
def corner(vth=VTH0, muf=1.0):
    """(lib path, section) for a global corner. The nominal corner returns None (keep fitc10.lib as built).
    Other corners are written to models/eh_<section>.lib (fitc10 values except VTH0 and MU)."""
    if abs(vth - VTH0) < 1e-9 and abs(muf - 1.0) < 1e-9:
        return None
    sec = f"eh_v{round(vth * 1e4):05d}_m{round(muf * 1e4):05d}"
    f = MODELS / f"{sec}.lib"
    if not f.exists():
        txt = (f"* energy_host corner: |V_th| {vth:.4f} V, mobility x{muf:.4f} (fitc10 otherwise). Aging/drift PROXY.\n"
               f".lib {sec}\n.param MU={MU0 * muf:.6f} CI=0.70e-6 SS=0.112 RCW=490 JOFF=1e-14 VTH0={vth:.4f} LOV=2\n.endl {sec}\n")
        tmp = f.with_suffix(f".tmp{os.getpid()}")
        tmp.write_text(txt)
        os.replace(tmp, f)
    return str(f), sec


# ----------------------------------------------------------------------------- instrumentation
def block_of(name):
    n = name[1:]
    if name.startswith("XNP"):
        return "latch"
    if name in ("XI1", "XI2", "XWR"):
        return "lock"
    k = int(n)
    if k <= 30:
        return "xbar"
    if k <= 60:
        return "dummy"
    if k <= 64:
        return "servo"
    if k <= 66:
        return "lshift"
    if k <= 74:
        return "sampler"
    if k <= 79:
        return "rreset"
    if k == 80:
        return "lock"
    if k <= 130:
        r = (k - 81) % 10
        return "comp" if r <= 2 else ("latch" if r <= 7 else "lock")
    return "spare"


# The five reporting blocks requested by the campaign specification, built from the finer groups above.
BLOCKS5 = {"crossbar": ["xbar"], "rails_reset": ["rreset"], "comparators": ["comp"], "latch_lock": ["latch", "lock"],
           "reference": ["dummy", "sampler", "servo", "lshift"], "spares": ["spare"]}


def instrument(t):
    """Split vdd, the host lines and vls (comparator sense sources) per block through 0 V ammeters."""
    used = set()

    def sub(m):
        name, pins, rest = m.group(1), [m.group(2), m.group(3), m.group(4)], m.group(5)
        b = block_of(name)
        for i, p in enumerate(pins):
            if p == "vdd" or p in HOST_LINES or (p == "vls" and b == "comp"):
                used.add((p, b))
                pins[i] = f"{p}_{b}"
        return f"{name} {' '.join(pins)} {rest}"
    t, n = re.subn(r"^(X\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(potft(?:seg)?\s.*)$", sub, t, flags=re.M)
    assert n >= 134, n
    am = "\n".join(f"VAM_{p}_{b} {p} {p}_{b} 0" for p, b in sorted(used))
    t, k = re.subn(r"^(VDD\s+vdd\s+0\s+.*)$", r"\g<1>\n* ---- energy_host ammeters (0 V, measurement only) ----\n" + am, t, flags=re.M)
    assert k == 1
    return t, sorted(used)


# ----------------------------------------------------------------------------- build
def row_pwl(x_i, V1, V2, T1, WMIN, GAP=5.0, cal_k=1.0, tr=0.2, rows_off=None, o=300.0, Vcal=None):
    """build_A's row PWL with an optional calibration-duration factor cal_k (rows at V1 for 8*cal_k us; everything
    after calibration shifts by 8*(cal_k-1) us) and an optional early row-off time (rows back to 3.3 V)."""
    sh = 8.0 * (cal_k - 1.0)
    t0 = o + 12.5 + sh
    tC2 = t0 + WMIN + T1 + GAP
    w = WMIN + x_i * T1
    Vc = V1 if Vcal is None else round(Vcal, 4)
    s = (f"PWL(0 3.3 {o+1:.1f}u 3.3 {o+2:.1f}u {Vc} {o+10+sh:.1f}u {Vc} {o+11+sh:.1f}u 3.3 "
         f"{t0:.2f}u 3.3 {t0+tr:.2f}u {V1} {t0+w:.2f}u {V1} {t0+w+tr:.2f}u 3.3 "
         f"{tC2:.2f}u 3.3 {tC2+tr:.2f}u {V2}")
    if rows_off is not None:
        s += f" {rows_off:.3f}u {V2} {rows_off+tr:.3f}u 3.3"
    return s + ")", tC2


def build(dst, idx=None, prior=WARM, vth=VTH0, muf=1.0, V1=None, V2=None, T1=170.0, WMIN=20.0, cal_k=1.0,
          trace=C.TRACE_US, rows_off=None, t_end=None, mc=None, inst=True, x=None, rstb_rel=None, adaptive=None,
          cold=False, reset_ext=0.0, Vcal=None):
    """Variant 3 netlist with host-side options. V1/V2 default to the 0.65 V formula levels (1.82/2.40 V).
    cal_k scales the calibration (sampling) duration; rows_off returns the rows to 3.3 V at that time (us);
    t_end overrides the simulation end (us); rstb_rel moves the rstb (latch precharge) release (us, default 150).
    adaptive=D (us): host option O1. An ideal host model (not part of the die) watches the five outputs na1-5; D us after
      the first one exceeds 1.65 V (after 320 us) every row is driven back to 3.3 V (0.2 us edge). Implemented as an
      ideal detector + timer (B-sources, 1 F integrator) and a series B-source per row, so the row current still flows
      through VR<i> and the die-side row node is row<i> (energy accounting unchanged).
    Vcal: calibration row level (default = V1; C1 always uses V1).
    reset_ext=X (us): the reset phase is X us longer (rows, phib/phi, rstr and C1/C2 all shift by X; rstb unchanged).
    cold=True: host option O2 (VDD power-gated idle). No warm state: every node starts at 0 V with VDD and all host
      lines at 0 V; VDD, the rows and phi ramp to their protocol levels over 0-10 us; rstr is low from t = 0.
    Returns dict(tC2, phases, levels, ...)."""
    dst = pathlib.Path(dst)
    x = C.XTE[idx] if x is None else x
    V1d, V2d = formula_levels(VTH0)
    V1 = V1d if V1 is None else round(V1, 4)
    V2 = V2d if V2 is None else round(V2, 4)
    cwd = os.getcwd()
    os.chdir(dst.parent)
    try:
        tC2 = build_A.build(str(dst), x, str(prior), vth="065", T1=T1, WMIN=WMIN, TRACE=trace, V1=V1, V2=V2)
    finally:
        os.chdir(cwd)
    t = dst.read_text()
    # ---- Variant 3 resize: identical to fitc10_campaign/scripts/common.py::build(variant=3) ----
    t, n = re.subn(r"^(CRAIL[1-5]\s+ap[1-5]\s+0\s+)375\.0p",
                   lambda m: f"{m.group(1)}{C.CRAIL_PF * C.CRAIL_SCALE:.2f}p", t, flags=re.M)
    assert n == 5, n
    t, n = re.subn(r"^(CREF\s+ref\s+0\s+)24\.0p", lambda m: f"{m.group(1)}{C.CREF_PF * C.CRAIL_SCALE:.2f}p", t, flags=re.M)
    assert n == 1, n
    changed = []

    def load_resize(m):
        name, mid, L, rest = m.groups()
        Ln = float(L) * C.LOAD_L_SCALE
        changed.append(name)
        return f"{name}{mid}{Ln:g}{rest}"
    t = re.sub(r"^(X\S+)(\s+0\s+0\s+\S+\s+potft\s+W=\S+\s+L=)(\S+)(.*)$", load_resize, t, flags=re.M)
    assert len(changed) == 19, changed
    cn = corner(vth, muf)
    if cn:
        t, n = re.subn(r"^\.lib \.\./models/fitc10\.lib fitc10$", f".lib {cn[0]} {cn[1]}", t, flags=re.M)
        assert n == 1
    draws = None
    if mc:
        t, draws = C.apply_mc(t, **mc)
    t = t.replace("TRACE-2 FINAL (frozen)", "TRACE-2 FINAL (frozen) + fitc10 resize Variant 3", 1)
    # ---- host-side options (none set = common.build output) ----
    sh = 8.0 * (cal_k - 1.0) + reset_ext
    if cal_k != 1.0 or rows_off is not None or reset_ext or Vcal is not None:
        for i in range(6):
            pwl, tC2 = row_pwl(float(x[i]), V1, V2, T1, WMIN, cal_k=cal_k, rows_off=rows_off, o=300.0 + reset_ext, Vcal=Vcal)
            t, n = re.subn(rf"^(VR{i+1}\s+row{i+1}\s+0\s+).*$", lambda m: m.group(1) + pwl, t, flags=re.M)
            assert n == 1
    if cal_k != 1.0 or reset_ext:
        t, n = re.subn(r"^V_PHIB\s.*$", f"V_PHIB phib 0 PWL(0 0 {309+sh:.1f}u 0 {310+sh:.1f}u 3.3)", t, flags=re.M); assert n == 1
        t, n = re.subn(r"^V_PHI\s.*$", f"V_PHI phi 0 PWL(0 3.3 {309+sh:.1f}u 3.3 {310+sh:.1f}u 0)", t, flags=re.M); assert n == 1
        t, n = re.subn(r"^V_RSTR\s.*$", f"V_RSTR rstr 0 PWL(0 3.3 20.0u 0.00 {311.5+sh:.1f}u 0.00 {312.5+sh:.1f}u 3.3)", t, flags=re.M); assert n == 1
    if rstb_rel is not None:
        t, n = re.subn(r"^V_RSTB\s.*$", f"V_RSTB rstb 0 PWL(0 0 {rstb_rel:.1f}u 0 {rstb_rel+1:.1f}u 3.3)", t, flags=re.M); assert n == 1
    if adaptive is not None:
        host = ["* ---- host model O1 (ideal, NOT part of the die): adaptive race end ----",
                "Bhflag hflag 0 V = ((time > 320e-6) && (max(max(max(v(na1), v(na2)), max(v(na3), v(na4))), v(na5)) > 1.65)) ? 1 : 0",
                "Ghint 0 htime hflag 0 1", "Chint htime 0 1", "Rhint htime 0 1e12"]
        for i in range(1, 7):
            t, n = re.subn(rf"^VR{i}\s+row{i}\s+0\s+", f"VR{i} rowpre{i} 0 ", t, flags=re.M); assert n == 1
            host.append(f"Brow{i} row{i} rowpre{i} V = (3.3 - v(rowpre{i})) * min(max((v(htime) - {adaptive * 1e-6:.4e}) / 0.2e-6, 0), 1)")
        t, n = re.subn(r"^(VDD\s+vdd\s+0\s+DC 3\.30)$", lambda m: m.group(1) + "\n" + "\n".join(host), t, flags=re.M); assert n == 1
    if cold:
        t, n = re.subn(r"^VDD\s+vdd\s+0\s+DC 3\.30$", "VDD vdd 0 PWL(0 0 10u 3.3)", t, flags=re.M); assert n == 1
        for i in range(1, 7):
            t, n = re.subn(rf"^(VR{i}\s+\S+\s+0\s+)PWL\(0 3\.3 ", r"\g<1>PWL(0 0 10u 3.3 ", t, flags=re.M); assert n == 1
        t, n = re.subn(r"^(V_PHI\s+phi\s+0\s+)PWL\(0 3\.3 ", r"\g<1>PWL(0 0 10u 3.3 ", t, flags=re.M); assert n == 1
        t, n = re.subn(r"^(V_RSTR\s+rstr\s+0\s+)PWL\(0 3\.3 20\.0u 0\.00 ", r"\g<1>PWL(0 0 ", t, flags=re.M); assert n == 1
        t, n = re.subn(r"^\.ic .*$", ".ic v(vboot)=0   $ cold start (host option O2): every source at 0 V at t = 0; only the floating dummy node vboot is pinned, as in the warm runs", t, flags=re.M); assert n == 1
    tend = tC2 + trace if t_end is None else t_end
    if t_end is not None or cal_k != 1.0 or reset_ext:
        t, n = re.subn(r"^\.tran .*$", f".tran 100n {tend:.0f}u 0 100n", t, flags=re.M); assert n == 1
    am = []
    if inst:
        t, am = instrument(t)
    dst.write_text(t)
    phases = dict(reset=(0.0, 301.0 + reset_ext), calibration=(301.0 + reset_ext, 312.5 + sh), C1=(312.5 + sh, tC2))
    return dict(tC2=tC2, t_end=float(re.search(r"^\.tran \S+ (\S+)u", t, re.M).group(1)), V1=V1, V2=V2, T1=T1,
                WMIN=WMIN, cal_k=cal_k, rows_off=rows_off, adaptive=adaptive, cold=cold, reset_ext=reset_ext, Vcal=Vcal, phases=phases, ammeters=am, draws=draws, corner=cn,
                vth=vth, muf=muf)


# ----------------------------------------------------------------------------- simulate
def read_raw(path):
    """ngspice binary raw (real, transient) -> {name: array}."""
    b = pathlib.Path(path).read_bytes()
    i = b.index(b"Binary:\n")
    hdr = b[:i].decode(errors="replace").splitlines()
    nv = int(next(l for l in hdr if l.startswith("No. Variables")).split(":")[1])
    npnt = int(next(l for l in hdr if l.startswith("No. Points")).split(":")[1])
    k = hdr.index("Variables:")
    names = [hdr[k + 1 + j].split()[1].lower() for j in range(nv)]
    d = np.frombuffer(b[i + 8:i + 8 + 8 * nv * npnt], dtype="<f8").reshape(npnt, nv)
    return {n: d[:, j].copy() for j, n in enumerate(names)}


def simulate(net, tag, vecs, timeout=7200, opts=C.RELAX):
    net = pathlib.Path(net)
    txt = re.sub(r"(?is)^\.control.*?^\.endc\s*$", "", net.read_text(), flags=re.M)
    ctl = [opts, ".control", "set filetype=binary", "run", f"write {tag}.raw " + " ".join(vecs), "quit", ".endc"]
    i = txt.rstrip().rfind("\n.end")
    run = net.with_name(f"_{tag}.cir")
    run.write_text(txt[:i] + "\n" + "\n".join(ctl) + txt[i:])
    s = time.time()
    r = subprocess.run(["ngspice", "-b", run.name], cwd=run.parent, capture_output=True, text=True,
                       timeout=timeout, stdin=subprocess.DEVNULL)
    info = dict(wall_s=round(time.time() - s, 1), returncode=r.returncode,
                warnings=[l.strip() for l in (r.stdout + r.stderr).splitlines()
                          if re.search(r"error|abort|singular|too small|failed", l, re.I)][:20])
    raw = run.with_name(f"{tag}.raw")
    if not raw.exists():
        info["error"] = "no data"
        (run.with_name(f"{tag}.log")).write_text(r.stdout[-5000:] + r.stderr[-5000:])
        return None, info
    d = read_raw(raw)
    raw.unlink()
    run.unlink()
    return d, info


def vec_list(ammeters):
    v = [f"v({n})" for n in C.NODES + [f"row{i}" for i in range(1, 7)] + ["vdd"]]
    v += [f"i({s})" for s in SOURCES] + [f"i(VAM_{p}_{b})" for p, b in ammeters]
    return v


# ----------------------------------------------------------------------------- energy
def _integ(t, y, a, b):
    """Trapezoid integral of y over [a, b] (seconds), with linear interpolation at the ends."""
    if b <= a:
        return 0.0
    m = (t > a) & (t < b)
    tt = np.concatenate([[a], t[m], [b]])
    yy = np.concatenate([[np.interp(a, t, y)], y[m], [np.interp(b, t, y)]])
    return float(np.trapezoid(yy, tt))


def energy(d, b, lock_us):
    """Energy per source and per block, per phase. Sign: E > 0 = delivered INTO the die.
    net: integral of v*i_out. pos: integral of max(v*i_out, 0) (energy the host pushes in; energy the die returns is
    not credited). host33: 3.3 V * integral of max(i_out, 0) (charge a driver powered from a 3.3 V host rail draws;
    returned charge goes to ground)."""
    t = d["time"]
    ph = dict(b["phases"])
    tc2, tend = b["tC2"], b["t_end"]
    tl = lock_us if (lock_us is not None and tc2 < lock_us < tend) else tend
    ph["C2_race"] = (tc2, tl)
    ph["post_lock"] = (tl, tend)
    ph["total"] = (0.0, tend)
    out = dict(phases_us={k: [round(a, 3), round(c, 3)] for k, (a, c) in ph.items()}, source={}, block={})
    for s, node in SOURCES.items():
        i_out = -d[f"i({s.lower()})"]
        v = d[f"v({node})"]
        p = v * i_out
        e = {}
        for k, (a, c) in ph.items():
            e[k] = dict(net=_integ(t, p, a * 1e-6, c * 1e-6), pos=_integ(t, np.maximum(p, 0), a * 1e-6, c * 1e-6),
                        host33=VDD * _integ(t, np.maximum(i_out, 0), a * 1e-6, c * 1e-6))
        out["source"][s] = e
    for p_, b_ in b["ammeters"]:
        i = d[f"i(vam_{p_}_{b_})"]
        v = d[f"v({p_})"]
        pw = v * i
        e = {}
        for k, (a, c) in ph.items():
            e[k] = dict(net=_integ(t, pw, a * 1e-6, c * 1e-6), host33=VDD * _integ(t, np.maximum(i, 0), a * 1e-6, c * 1e-6))
        out["block"][f"{p_}:{b_}"] = e
    # closure: sum of ammeter currents into blocks vs each source's output current (unsplit loads: 1T resistors, caps)
    clos = {}
    for s, node in SOURCES.items():
        tot = sum(d[f"i(vam_{p_}_{b_})"] for p_, b_ in b["ammeters"] if p_ == node)
        if isinstance(tot, int):
            continue
        clos[s] = float(_integ(t, np.abs(-d[f"i({s.lower()})"] - tot), 0, tend * 1e-6) /
                        max(_integ(t, np.abs(d[f"i({s.lower()})"]), 0, tend * 1e-6), 1e-30))
    out["closure_rel"] = clos
    return out


def binned_power(d, dt_us=1.0):
    """Per-source power averaged over dt_us bins (bin energy / dt), so the stored traces conserve energy."""
    t = d["time"]
    edges = np.arange(0, t[-1] + 1e-12, dt_us * 1e-6)
    out = {}
    for s, node in SOURCES.items():
        p = -d[f"v({node})"] * d[f"i({s.lower()})"]
        cum = np.concatenate([[0], np.cumsum(0.5 * (p[1:] + p[:-1]) * np.diff(t))])
        ce = np.interp(edges, t, cum)
        out[s] = np.diff(ce) / (dt_us * 1e-6)
    return edges[:-1], out


# ----------------------------------------------------------------------------- run
def run(job):
    """job: dict(tag, idx, outdir, [build kwargs...], [wdir], [save_wave], [save_prior], [vth_metric]).
    Writes <tag>.json (metrics + energy + build info), <tag>.csv.gz (1 us waveforms + binned source power) and
    <tag>.cir.gz."""
    outdir = pathlib.Path(job["outdir"])
    outdir.mkdir(parents=True, exist_ok=True)
    wd = C.workdir(f'eh_{job.get("wdir", "runs")}')
    net = wd / f"{job['tag']}.cir"
    bk = {k: job[k] for k in ("prior", "vth", "muf", "V1", "V2", "T1", "WMIN", "cal_k", "trace", "rows_off", "t_end",
                              "mc", "inst", "x", "rstb_rel", "adaptive", "cold", "reset_ext", "Vcal") if k in job}
    b = build(net, job["idx"], **bk)
    d, info = simulate(net, job["tag"], vec_list(b["ammeters"]))
    meta = dict(tag=job["tag"], idx=job["idx"], label=int(C.YTE[job["idx"]]) + 1, job={k: (str(v) if isinstance(v, pathlib.PurePath) else v)
                for k, v in job.items() if k not in ("outdir", "x")}, run=info,
                build={k: v for k, v in b.items() if k not in ("draws", "ammeters")})
    if d is not None:
        t = d["time"]
        v = {n: d[f"v({n})"] for n in C.NODES}
        m = C.metrics(t, v, b["tC2"], vth=job.get("vth_metric", 0.65))
        meta.update(m)
        meta["race_us"] = round(min(m["trip_us"].values()) - b["tC2"], 3) if m["trip_us"] else None
        bE = b
        if b.get("adaptive") is not None:
            # O1: the classification ends T_CLS_TAIL us after the rows are back at 3.3 V; read the outputs there
            if m["trip_us"]:
                tcls = min(m["trip_us"].values()) + b["adaptive"] + 0.2 + T_CLS_TAIL
            else:
                tcls = b["t_end"]
            bE = dict(b, t_end=tcls)
            meta["t_cls_us"] = round(tcls, 3)
            meta["latched_at_cls"] = [k for k in range(1, 6) if np.interp(tcls * 1e-6, t, v[f"na{k}"]) > 2.5]
            meta["na_at_cls"] = {k: round(float(np.interp(tcls * 1e-6, t, v[f"na{k}"])), 4) for k in range(1, 6)}
        meta["energy"] = energy(d, bE, m["lock_us"]) if b["ammeters"] else None
        if job.get("save_prior"):
            if b.get("adaptive") is not None:
                save_prior_at(job["save_prior"], t, v, bE["t_end"] * 1e-6)
            else:
                C.save_prior(job["save_prior"], t, v)
        if job.get("save_wave", True):
            tb, pw = binned_power(d)
            cols = [tb * 1e6] + [np.interp(tb, t, d[f"v({n})"]) for n in C.NODES] + [pw[s] * 1e6 for s in SOURCES]
            with gzip.open(outdir / f"{job['tag']}.csv.gz", "wt") as f:
                f.write("t_us," + ",".join(C.NODES) + "," + ",".join(f"P_{s}_uW" for s in SOURCES) + "\n")
                np.savetxt(f, np.column_stack(cols), fmt="%.5g", delimiter=",")
        if job.get("save_end"):   # every saved node's final value (for standby continuation)
            meta["end_state"] = {n: float(d[f"v({n})"][-1]) for n in C.NODES + ["vdd"]}
    (outdir / f"{job['tag']}.json").write_text(json.dumps(meta, indent=1, default=float))
    with open(net) as f, gzip.open(outdir / f"{job['tag']}.cir.gz", "wt") as g:
        g.write(f.read())
    if b["draws"]:
        (outdir / f"{job['tag']}_draws.json").write_text(json.dumps(b["draws"]))
    net.unlink()
    return meta


def run_cached(job):
    """eh.run, but returns the saved JSON if this tag already finished (restart-safe)."""
    f = pathlib.Path(job["outdir"]) / f"{job['tag']}.json"
    return json.load(open(f)) if f.exists() else run(job)


T_CLS_TAIL = 10.0   # us between the rows returning to 3.3 V and the end of an O1 classification (outputs read there)


def save_prior_at(path_tag, t, v, t_at):
    """Like common.save_prior, but the state at time t_at (the 5 saved points just before t_at)."""
    k = int(np.searchsorted(t, t_at))
    tt = t[:k]
    vv = {n: x[:k] for n, x in v.items()}
    C.save_prior(path_tag, tt, vv)


def pool_run(jobs, nproc=4, log=None):
    from multiprocessing import Pool
    seen = set()
    jobs = [j for j in jobs if not (pathlib.Path(j["outdir"]) / f"{j['tag']}.json").exists()
            and not (j["tag"] in seen or seen.add(j["tag"]))]
    s = time.time()
    with Pool(nproc) as p:
        for k, m in enumerate(p.imap_unordered(run, jobs), 1):
            print(f"[{k}/{len(jobs)} {time.time()-s:6.0f}s] {m['tag']} label {m['label']} latched {m.get('latched')} "
                  f"valid {m.get('valid')} {m.get('failure')} race {m.get('race_us')} wall {m['run']['wall_s']}", flush=True)
