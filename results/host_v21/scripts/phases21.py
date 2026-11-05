"""Host protocol v2.1 evaluation phases (DECISIONS P2/P3). Resumable: every run/calibration skips finished work.
Usage: python3 phases21.py nominal | E1cal | E1 | E1forced | E1chain | E1idle [nproc]"""
import json, sys
import numpy as np
import hv21, hv2, eh, common as C

SUB = eh.SUB                                             # the fixed 20-sample subset (fitc10 phase3_subset.json)
E1_VTH = (0.49, 0.51, 0.53, 0.55, 0.57, 0.59, 0.61)       # lower-edge sweep (P3.1)
FORCED_W = (0.61,)                                       # forced-mode reference (P3.2)
CHAIN_VTH = 0.51                                         # mode-W chain (P3.3)


def ckey(vth, muf=1.0, forced=None):
    return f"v{round(vth*1000):04d}_m{round(muf*100):03d}" + (f"_forced{forced}" if forced else "")


def cal(vth, muf=1.0, forced=None):
    hv21.design_W()
    return hv21.calibrate(ckey(vth, muf, forced), vth, muf, None, force_mode=forced)


def cls_job(phase, c, i, tagp=None, **kw):
    V1, V2 = c["levels"]
    tag = f"{phase}_{c['key']}_{tagp or 'v21'}_s{i:02d}"
    return dict(tag=tag, idx=i, outdir=hv21.RAW / phase, wdir=phase, vth=c["vth"], muf=c["muf"], mc=c["mc"], V1=V1, V2=V2,
                k=c["k"], mode=c["mode"], prior_state=c["start_state"], vth_metric=c["vth"], cal_key=c["key"],
                policy="forced" if c.get("mode_forced") else "v2.1", **kw)


def idle_after(m):
    """The idle that follows a classification (P2.4): 1 s VDD on (mode W) or 1 s off (mode G), from the read state."""
    j = m["job"]
    return hv21.run_idle(m["tag"] + "_idle", hv21.RAW / "E1idle", m["end_state_read"], m["mode"], vth=j["vth"],
                         muf=j["muf"], mc=j.get("mc"))


def _idle(tag):
    import pathlib
    for d in ("E1", "E1forced"):
        f = hv21.RAW / d / f"{tag}.json"
        if f.exists():
            return idle_after(json.load(open(f)))


def chain(phase, c, idxs, tagp="chain"):
    st = c["start_state"]
    for n, i in enumerate(idxs):
        j = cls_job(phase, c, i)
        j.update(tag=f"{phase}_{tagp}_{c['key']}_{n:02d}_s{i:02d}", prior_state=st, chain_step=n)
        m = hv21.run_cls(j)
        st = hv21.idle_state(f"{phase}_{tagp}_{c['key']}_{n:02d}_idle", hv21.RAW / phase, m["end_state_read"], c["mode"],
                             c["vth"], c["muf"], c["mc"])
        print(f"chain {n} s{i} mode {c['mode']} read {m.get('latched_read')} {m.get('failure_read')} race {m.get('race_us')}", flush=True)


if __name__ == "__main__":
    w = sys.argv[1]
    n = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 4
    from multiprocessing import Pool
    if w == "nominal":
        print(json.dumps({k: v for k, v in cal(0.65).items() if k != "start_state"}, indent=1, default=float))
    elif w == "E1cal":
        hv21.design_W()
        with Pool(n) as p:
            p.map(cal, list(E1_VTH))
    elif w == "E1":
        js = [cls_job("E1", cal(v), i) for v in E1_VTH for i in SUB]
        hv21.pool_run(hv21.run_cls, js, n)
    elif w == "E1forced":
        js = [cls_job("E1forced", cal(v, forced="W"), i) for v in FORCED_W for i in SUB]
        hv21.pool_run(hv21.run_cls, js, n)
    elif w == "E1chain":
        chain("E1chain", cal(CHAIN_VTH), SUB)
    elif w == "E1idle":
        import glob, pathlib
        tags = [pathlib.Path(f).stem for d in ("E1", "E1forced") for f in sorted(glob.glob(str(hv21.RAW / d / "*.json")))]
        with Pool(n) as p:
            p.map(_idle, tags)
