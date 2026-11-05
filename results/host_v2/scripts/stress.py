"""C2: gate-dielectric stress audit under host protocol v2 (DECISIONS H3). Five runs, the fitc10 Phase 2 input picks
(maxsum, minsum, maxcol, mincol) plus a chained step, at the nominal die with the nominal calibration, each simulated
through (1) the VDD power-up and the whole classification (full resolution, every top-level node), and (2) the
VDD power-down and 1 s off-period that follows. For EVERY TFT: max |V_GS| and |V_GD| from terminal voltages vs 3.5 V.
-> summary/c2_stress.json, summary/c2_devices.csv, raw/C2/"""
import csv, json, re, sys
import numpy as np
from multiprocessing import Pool
import hv2, eh, common as C
sys.path.insert(0, str(C.CAMP / "scripts"))
import phase2_audit as P2   # read-only: pick() and the ASCII raw reader

LIM = 3.5
OUT = hv2.RAW / "C2"


def top_nodes(txt):
    return sorted({n.lower() for l in txt.splitlines() if re.match(r"^[XxMmCcRrVvBb]", l)
                   for n in l.split()[1:4] if re.match(r"^[a-z_][a-z0-9_]*$", n.lower())
                   and n.lower() not in ("potft", "potftseg", "pwl", "dc", "v")})


def audit_net(net, d):
    t = d["time"]
    V = lambda n: np.zeros_like(t) if n == "0" else d.get(f"v({n})")
    devs = []
    for l in open(net):
        mm = re.match(r"^(X\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(potft(?:seg)?)\s+W=(\S+)\s+L=(\S+)", l)
        if not mm:
            continue
        name, dn, g, s, mod, W, Lc = mm.groups()
        vd, vg, vs = V(dn.lower()), V(g.lower()), V(s.lower())
        assert vd is not None and vg is not None and vs is not None, (name, dn, g, s)
        gs, gd = np.abs(vg - vs), np.abs(vg - vd)
        st = np.maximum(gs, gd)
        k = int(np.argmax(st))
        devs.append(dict(device=name, crossbar=mod == "potftseg", d=dn, g=g, s=s, W=float(W), L=float(Lc),
                         max_vgs=round(float(gs.max()), 4), max_vgd=round(float(gd.max()), 4), max_stress=round(float(st[k]), 4),
                         t_max_us=round(float(t[k] * 1e6), 3), margin_V=round(LIM - float(st[k]), 4)))
    return devs


def run(job):
    tag = job["tag"]
    f = OUT / f"{tag}.json"
    if f.exists():
        return json.load(open(f))
    OUT.mkdir(parents=True, exist_ok=True)
    wd = C.workdir("hv2_c2")
    net = wd / f"{tag}.cir"
    b = hv2.build_cls(net, job["idx"], vth=0.65, muf=1.0, V1=job["V1"], V2=job["V2"], k=job["k"], prior_state=job["prior_state"])
    nodes = top_nodes(net.read_text())
    d, info = hv2.simulate(net, tag, [f"v({n})" for n in nodes], stop_htime_us=b["stop_htime_us"], opts=C.RELAX)
    m, t_read = hv2.metrics_v2(d, b, 0.65)
    devs = audit_net(net, d)
    st = hv2.state_at(d, t_read * 1e-6)
    net.unlink()
    # power-down + 1 s off, every top-level node saved
    netoff = wd / f"{tag}_off.cir"
    eh.build(netoff, 0, inst=False)
    txt = netoff.read_text()
    dn = "PWL(0 3.3 1u 3.3 11u 0)"
    txt = re.sub(r"^VDD\s+vdd\s+0\s+.*$", f"VDD vdd 0 {dn}", txt, flags=re.M)
    for i in range(1, 7):
        txt = re.sub(rf"^(VR{i}\s+row{i}\s+0\s+).*$", rf"\g<1>{dn}", txt, flags=re.M)
    for nm, node in (("V_RSTR", "rstr"), ("V_RSTB", "rstb"), ("V_PHIB", "phib")):
        txt = re.sub(rf"^{nm}\s.*$", f"{nm} {node} 0 {dn}", txt, flags=re.M)
    txt = re.sub(r"^V_PHI\s.*$", "V_PHI phi 0 DC 0", txt, flags=re.M)
    txt = re.sub(r"^\.ic .*$", hv2.ic_line(st), txt, flags=re.M)
    txt = re.sub(r"^\.tran .*$", ".tran 100n 1 0 2.5m", txt, flags=re.M)
    netoff.write_text(txt)
    d2, info2 = hv2.simulate(netoff, tag + "_off", [f"v({n})" for n in top_nodes(txt)])
    devs_off = audit_net(netoff, d2)
    netoff.unlink()
    rec = dict(tag=tag, idx=job["idx"], pick=job["pick"], run=info, run_off=info2, outcome=dict(read=m["latched_read"], failure=m["failure_read"]),
               t_read_us=t_read, devices=devs, devices_off=devs_off,
               worst=max(devs, key=lambda x: x["max_stress"]), worst_off=max(devs_off, key=lambda x: x["max_stress"]),
               n_above=sum(x["max_stress"] > LIM for x in devs), n_above_off=sum(x["max_stress"] > LIM for x in devs_off),
               min_node_V=float(min(np.min(d[f"v({n})"]) for n in nodes)), min_node_V_off=float(min(np.min(d2[f"v({n})"]) for n in top_nodes(txt))),
               end_state_read=st)
    f.write_text(json.dumps(rec, indent=1, default=float))
    return rec


if __name__ == "__main__":
    import phases
    c = phases.cal(0.65, 1.0)
    sel = P2.pick()
    base = dict(V1=c["levels"][0], V2=c["levels"][1], k=c["k"])
    js = [dict(tag=f"C2_{k}_s{i:02d}", idx=i, pick=k, prior_state=c["start_state"], **base) for k, i in sel.items()]
    with Pool(4) as p:
        res = p.map(run, js)
    # chained step: #31 started from the 1 s-off state after #30 (as fitc10 Phase 2 used chain step #31)
    m30 = hv2.run_cls(dict(tag="C2_chainprev_s30", idx=30, outdir=OUT, wdir="c2", V1=base["V1"], V2=base["V2"], k=base["k"],
                           prior_state=c["start_state"], vth_metric=0.65))
    st = hv2.off_state("C2_chainprev_s30_off", OUT, m30["end_state_read"], 0.65, 1.0, None)
    res.append(run(dict(tag="C2_chain_s31", idx=31, pick="chain", prior_state=st, **base)))
    alld = [dict(run=r["tag"], phase="classification", **x) for r in res for x in r["devices"]] + \
           [dict(run=r["tag"], phase="power_down_off", **x) for r in res for x in r["devices_off"]]
    with open(hv2.SUMM / "c2_devices.csv", "w", newline="") as g:
        w = csv.DictWriter(g, fieldnames=list(alld[0]))
        w.writeheader(); w.writerows(alld)
    per_dev = {}
    for x in alld:
        if x["device"] not in per_dev or x["max_stress"] > per_dev[x["device"]]["max_stress"]:
            per_dev[x["device"]] = x
    top = sorted(per_dev.values(), key=lambda x: -x["max_stress"])[:12]
    xb = max((x for x in alld if x["crossbar"]), key=lambda x: x["max_stress"])
    json.dump(dict(limit_V=LIM, runs={r["tag"]: dict(pick=r["pick"], idx=r["idx"], outcome=r["outcome"], n_above=r["n_above"],
                                                     n_above_off=r["n_above_off"], worst=r["worst"], worst_off=r["worst_off"],
                                                     min_node_V=r["min_node_V"], min_node_V_off=r["min_node_V_off"]) for r in res},
                   n_devices=len(per_dev), n_above_any=sum(x["max_stress"] > LIM for x in per_dev.values()), top=top, crossbar_max=xb),
              open(hv2.SUMM / "c2_stress.json", "w"), indent=1, default=float)
    print(json.dumps(top[:5], indent=1, default=float))
