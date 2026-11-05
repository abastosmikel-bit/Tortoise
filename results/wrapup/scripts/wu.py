"""Wrap-up studies: shared tooling for results/wrapup.

Imports results/host_v21/scripts/hv21.py (and through it host_v2/hv2.py, energy_host/eh.py and the fitc10 campaign's
common.py) READ-ONLY. Nothing in an earlier folder is written: calibrations, runs and corner .lib files go to
results/wrapup/{raw,models}.

Tortoise v1.0 = Variant 3 at fitc10, weights rev10/eval/F_hw_m4_firstpass.npy, host protocol v2.1 (hv21, unchanged).
Circuit VARIANTS (Studies 2 and 3) are netlist transforms applied to the final netlist text just before ngspice runs
(hv2.simulate is wrapped), so they act identically on a1, idle and classification netlists. The active variant is a
per-process context (set_context); with variant None every netlist is the Tortoise v1.0 netlist, byte for byte.
"""
import json, os, pathlib, re, shutil, sys, time
sys.dont_write_bytecode = True
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import numpy as np

WU = pathlib.Path(__file__).resolve().parents[1]
REPO = WU.parents[1]
sys.path.insert(0, str(REPO / "results/host_v21/scripts"))
import hv21           # noqa: E402  (read-only)
import hv2            # noqa: E402
import eh             # noqa: E402
import common as C    # noqa: E402

RAW, SUMM, MODELS = WU / "raw", WU / "summary", WU / "models"
for _d in (RAW, SUMM, MODELS):
    _d.mkdir(parents=True, exist_ok=True)
CAL = RAW / "cal"
hv21.CAL = CAL                      # calibration sessions of this study are written here, never into host_v21
SUB = list(eh.SUB)                  # the fixed 20-sample test subset (fitc10 summary/phase3_subset.json)
HV2RAW, HV21RAW = REPO / "results/host_v2/raw", REPO / "results/host_v21/raw"

# ---------------------------------------------------------------- corners: byte-identical copies of earlier campaigns'
OLD_MODEL_DIRS = [REPO / "results/host_v21/models", REPO / "results/host_v2/models", REPO / "results/energy_host/models"]
eh.MODELS = MODELS


def corner(vth=eh.VTH0, muf=1.0):
    sec = f"eh_v{round(vth * 1e4):05d}_m{round(muf * 1e4):05d}"
    new = MODELS / f"{sec}.lib"
    if not new.exists() and not (abs(vth - eh.VTH0) < 1e-9 and abs(muf - 1.0) < 1e-9):
        for src in OLD_MODEL_DIRS:
            if (src / f"{sec}.lib").exists():
                tmp = new.with_suffix(f".tmp{os.getpid()}")
                shutil.copyfile(src / f"{sec}.lib", tmp)
                os.replace(tmp, new)
                break
    return hv2._eh_corner(vth, muf)   # the original eh.corner: writes MODELS/<sec>.lib only if still missing


eh.corner = corner

# ---------------------------------------------------------------- variant context and the simulate wrapper
CTX = dict(variant=None, in_cal=False, die=None)
VARIANTS = {}                       # name -> object with .apply(text, ctx) -> (text, extra_vectors) and .n_tft


def set_context(**kw):
    CTX.update(kw)


_simulate_orig = hv2.simulate


def _simulate(net, tag, vecs, *a, **kw):
    v = CTX.get("variant")
    if v:
        p = pathlib.Path(net)
        txt, extra = VARIANTS[v].apply(p.read_text(), CTX)
        p.write_text(txt)
        vecs = list(vecs) + [x for x in extra if x not in vecs]
    return _simulate_orig(net, tag, vecs, *a, **kw)


hv2.simulate = _simulate


def netlist_type(txt):
    """'cls' (classification, host model present), 'idleW', 'idleG' or 'a1'."""
    if re.search(r"^Bhflag ", txt, re.M):
        return "cls"
    vr1 = re.search(r"^VR1\s+\S+\s+0\s+(.*)$", txt, re.M).group(1)
    if vr1.startswith("DC 3.3"):
        return "idleW"
    if vr1.startswith("PWL(0 3.3 1u 3.3"):
        return "idleG"
    return "a1"


def pwl_pairs(s):
    vals = re.search(r"PWL\((.*)\)", s).group(1).split()
    out = []
    for i in range(0, len(vals) - 1, 2):
        t = vals[i]
        tt = float(t[:-1]) * 1e-6 if t.endswith("u") else float(t)
        out.append((tt, float(vals[i + 1])))
    return out


def cls_row_timing(txt):
    """From VR1's PWL in a classification netlist: (cold, t0_us, V1, tC2_us, k)."""
    s = re.search(r"^VR1\s+\S+\s+0\s+(PWL\(.*\))$", txt, re.M).group(1)
    pr = pwl_pairs(s)
    cold = pr[0][1] == 0.0
    drops = [i for i in range(1, len(pr)) if pr[i - 1][1] == 3.3 and pr[i][1] < 3.3 and pr[i - 1][0] > 20e-6]
    assert len(drops) >= 3, s
    t0 = pr[drops[1] - 1][0] * 1e6
    V1 = pr[drops[1]][1]
    tC2 = pr[drops[2] - 1][0] * 1e6
    k = (tC2 - t0 - hv2.WMIN - 5.0) / hv2.T1_BASE
    return cold, round(t0, 3), V1, round(tC2, 3), k


# ---------------------------------------------------------------- jobs, calibration, pools
def ckey(prefix, vth, muf, die=None, forced=None, variant=None):
    return (f"{prefix}_v{round(vth * 1000):04d}_m{round(muf * 100):03d}" + (f"_an{die['anchor']}d{die['die']:02d}" if die else "")
            + (f"_forced{forced}" if forced else "") + (f"_{variant}" if variant else ""))


def calibrate(key, vth, muf=1.0, mc=None, force_mode=None, variant=None, design=None):
    """hv21.calibrate (v2.1 P2.1) under an optional circuit variant; the bias row (if any) is held off during the
    whole calibration session (ctx in_cal). design: dict overriding the v2 design constants (variant design runs)."""
    set_context(variant=variant, in_cal=True)
    old = dict(hv21.DESIGN_V2)
    try:
        if design:
            hv21.DESIGN_V2.update(design)
        return hv21.calibrate(key, vth, muf, mc, force_mode=force_mode)
    finally:
        hv21.DESIGN_V2.clear(); hv21.DESIGN_V2.update(old)
        set_context(in_cal=False)


def cal_job(a):
    return calibrate(**a)


def cls_job(phase, c, i, tagp="v21", variant=None, **kw):
    V1, V2 = c["levels"]
    tag = f"{phase}_{c['key']}_{tagp}_s{i:02d}"
    j = dict(tag=tag, idx=i, outdir=RAW / phase, wdir=f"wu_{phase}", vth=c["vth"], muf=c["muf"], mc=c["mc"], V1=V1, V2=V2,
             k=c["k"], mode=c["mode"], prior_state=c["start_state"], vth_metric=c["vth"], cal_key=c["key"],
             policy="forced" if c.get("mode_forced") else "v2.1", variant=variant)
    j.update(kw)
    return j


def run_cls(job):
    set_context(variant=job.get("variant"), in_cal=False)
    m = hv21.run_cls(job)
    if job.get("idle") and "end_state_read" in m:
        jj = m["job"]
        hv21.run_idle(m["tag"] + "_idle", pathlib.Path(job["outdir"]).parent / (pathlib.Path(job["outdir"]).name + "idle"),
                      m["end_state_read"], m["mode"], vth=jj["vth"], muf=jj["muf"], mc=jj.get("mc"))
    return m


def pool_run(jobs, nproc=4, fn=run_cls):
    from multiprocessing import Pool
    seen = set()
    jobs = [j for j in jobs if not (pathlib.Path(j["outdir"]) / f"{j['tag']}.json").exists()
            and not (j["tag"] in seen or seen.add(j["tag"]))]
    s = time.time()
    with Pool(nproc, maxtasksperchild=1) as p:
        for kk, m in enumerate(p.imap_unordered(fn, jobs), 1):
            print(f"[{kk}/{len(jobs)} {time.time()-s:6.0f}s] {m['tag']} mode {m.get('mode')} label {m.get('label')} "
                  f"read {m.get('latched_read')} {m.get('failure_read')} race {m.get('race_us')} t_read {m.get('t_read_us')} "
                  f"wall {m['run']['wall_s']}", flush=True)


def build_cls_text(job):
    """The classification netlist text run_cls would simulate for this job (no simulation; for identity checks)."""
    set_context(variant=job.get("variant"), in_cal=False)
    wd = C.workdir("wu_buildcheck")
    net = wd / f"{job['tag']}_{os.getpid()}.cir"
    hv2.build_cls(net, job.get("idx"), x=job.get("x"), vth=job["vth"], muf=job["muf"], mc=job.get("mc"), V1=job["V1"],
                  V2=job["V2"], k=job["k"], prior_state=job["prior_state"], cold=(job["mode"] == "G"),
                  rstb_rel=hv2.RSTB_REL if job["mode"] == "G" else hv21.RSTB_REL_W)
    t = net.read_text()
    if job.get("variant"):
        t, _ = VARIANTS[job["variant"]].apply(t, CTX)
    net.unlink()
    return t


def norm_lib(txt):
    """Netlist text with the absolute corner .lib path reduced to its file name (models live in different folders)."""
    return re.sub(r"^\.lib \S*/(eh_\S+\.lib) ", r".lib \1 ", txt, flags=re.M)


def same_calibration(a, b, tol=1e-9):
    """True if two calibration records give identical host settings and start state."""
    if a.get("failed") or b.get("failed"):
        return False
    if a.get("mode", "G") != b.get("mode", "G") or list(a["levels"]) != list(b["levels"]) or abs(a["k"] - b["k"]) > tol:
        return False
    if list(a["race"]["t_us"]) != list(b["race"]["t_us"]):
        return False
    sa, sb = a["start_state"], b["start_state"]
    return set(sa) == set(sb) and all(abs(sa[n] - sb[n]) <= tol for n in sa)


def load_runs(phase, pattern="*.json"):
    return [json.load(open(f)) for f in sorted((RAW / phase).glob(pattern)) if not f.name.endswith("_draws.json")]
