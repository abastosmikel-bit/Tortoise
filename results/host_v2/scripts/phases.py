"""Host protocol v2 evaluation phases (DECISIONS H2/H3). Resumable: every run/calibration skips finished work.
Usage: python3 phases.py design | C1 | C1chain | C3 | C3ideal | C4 | C5 <v2|v1reset> | C6 [nproc]"""
import json, sys
import numpy as np
import hv2, eh, common as C

SUB = eh.SUB                                   # the fixed 20-sample subset (fitc10 phase3_subset.json)
DV = (0.0, 0.10, 0.20, 0.30, 0.35)
MU = (1.0, 0.85, 0.70, 0.60, 0.50)
C3_CELLS = [(round(0.65 + d, 2), m) for d in DV for m in MU]
C4_DIES = [dict(anchor=20, die=d, mc=dict(seed=20000 + d, s_vth=0.020, s_mu=0.10, s_rc=0.20, scale="pelgrom_vth")) for d in range(1, 6)]
C6_VTH = (0.45, 0.47, 0.49, 0.51, 0.53, 0.55)
C6B_VTH = (0.57, 0.59, 0.61)                   # H5 extension
CHAIN1 = list(range(30, 40))                   # C1 back-to-back chain: test samples 30-39 (as the fitc10 chain)


def design():
    if hv2.DESIGN_F.exists():
        return json.load(open(hv2.DESIGN_F))
    rec = hv2.calibrate("design_nominal", 0.65, 1.0, None, nominal=True)
    d = dict(a1_offset_V=rec["a1"]["vraw"] - 0.65, I_ref_uA=rec["a1"]["i_ov_uA"], race_offset_V=rec["race"]["vraw"] - 0.65,
             source="raw/cal/design_nominal (nominal die: |V_th| 0.65 V, mu x1, no mismatch)", a1=rec["a1"], race=rec["race"])
    json.dump(d, open(hv2.DESIGN_F, "w"), indent=1, default=float)
    return d


def ckey(vth, muf, die=None):
    return (f"v{round(vth*1000):04d}_m{round(muf*100):03d}" + (f"_an{die['anchor']}d{die['die']:02d}" if die else ""))


def cal(vth, muf, die=None):
    return hv2.calibrate(ckey(vth, muf, die), vth, muf, die["mc"] if die else None, design=design())


def cls_job(phase, c, i, vth, muf, mc=None, policy="learned", inst=False, **kw):
    if policy == "learned":
        V1, V2 = c["levels"]
        k = c["k"]
    else:   # 'ideal' reference: true |V_th| and true mu (labelled as such)
        V1, V2 = hv2.levels(vth)
        k = hv2.kfac(muf)
    tag = f"{phase}_{c['key']}_{policy}_s{i:02d}"
    return dict(tag=tag, idx=i, outdir=hv2.RAW / phase, wdir=phase, vth=vth, muf=muf, mc=mc, V1=V1, V2=V2, k=k,
                prior_state=c["start_state"], inst=inst, vth_metric=vth, policy=policy, cal_key=c["key"], **kw)


def chain(phase, c, idxs, vth, muf, mc=None, inst=False, tagp="chain", **kw):
    """Back-to-back classifications with a 1 s VDD-off between them; step 1 starts from the calibration start state."""
    st = c["start_state"]
    out = []
    for n, i in enumerate(idxs):
        j = cls_job(phase, c, i, vth, muf, mc, inst=inst, **kw)
        j.update(tag=f"{phase}_{tagp}_{n:02d}_s{i:02d}", prior_state=st, chain_step=n)
        m = hv2.run_cls(j)
        out.append(m)
        st = hv2.off_state(f"{phase}_{tagp}_{n:02d}_off", hv2.RAW / phase, m["end_state_read"], vth, muf, mc)
        print(f"chain {tagp} {n} s{i} read {m.get('latched_read')} {m.get('failure_read')} race {m.get('race_us')}", flush=True)
    return out


if __name__ == "__main__":
    w = sys.argv[1]
    n = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 4
    if w == "design":
        print(json.dumps(design(), indent=1, default=float))
    elif w == "C1":
        c = cal(0.65, 1.0)
        hv2.pool_run(hv2.run_cls, [cls_job("C1", c, i, 0.65, 1.0, inst=True) for i in range(90)], n)
    elif w == "C1chain":
        chain("C1", cal(0.65, 1.0), CHAIN1, 0.65, 1.0, inst=True)
    elif w == "C3cal":
        from multiprocessing import Pool
        with Pool(n) as p:
            p.starmap(cal, C3_CELLS)
    elif w == "C3":
        js = []
        for v, m in C3_CELLS:
            c = cal(v, m)
            js += [cls_job("C3", c, i, v, m) for i in SUB]
        hv2.pool_run(hv2.run_cls, js, n)
    elif w == "C4":
        from multiprocessing import Pool
        with Pool(n) as p:
            cs = p.starmap(cal, [(0.65, 1.0, d) for d in C4_DIES])
        hv2.pool_run(hv2.run_cls, [cls_job("C4", c, i, 0.65, 1.0, d["mc"]) for c, d in zip(cs, C4_DIES) for i in SUB], n)
    elif w == "C5":
        c = cal(0.65, 0.5)
        chain("C5", c, SUB, 0.65, 0.5, tagp="v2")
        chain("C5", c, SUB, 0.65, 0.5, tagp="v1reset", scale_reset=False)
    elif w == "C3ideal":
        fails = json.load(open(hv2.SUMM / "c3_aging.json"))["failing_cells"]
        js = []
        for v, m in fails:
            c = cal(v, m)
            js += [cls_job("C3", c, i, v, m, policy="ideal") for i in SUB]
        hv2.pool_run(hv2.run_cls, js, n)
    elif w == "C6b":
        cs = [cal(v, 1.0) for v in C6B_VTH]
        hv2.pool_run(hv2.run_cls, [cls_job("C6", c, i, v, 1.0) for c, v in zip(cs, C6B_VTH) for i in SUB], n)
    elif w == "C6":
        from multiprocessing import Pool
        with Pool(n) as p:
            cs = p.starmap(cal, [(v, 1.0) for v in C6_VTH])
        hv2.pool_run(hv2.run_cls, [cls_job("C6", c, i, v, 1.0) for c, v in zip(cs, C6_VTH) for i in SUB], n)
