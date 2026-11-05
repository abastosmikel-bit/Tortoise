"""E2: ramp-rate stress audit (DECISIONS P3.4). The v2 C2 audit (host_v2/scripts/stress.py, imported read-only: the
same 5 runs, the same per-TFT |V_GS|/|V_GD| audit over every top-level node) repeated at VDD ramp rates of 0.3x, 1x
and 3x the C2 rate (3.3 V in 10 us). The rate applies to the power-up (VDD, rows, phi: 0 -> level) and to the
power-down (every source -> 0 V). Nominal die (mode G under v2.1), levels from the v2.1 nominal calibration.
Start state at rate r: the read state of that calibration's race b, then a power-down at rate r and 1 s off.
Usage: python3 stress_ramp.py <rate> [<rate> ...]   (rate = 0.3 | 1 | 3 | extension rates)
-> raw/E2/*.json, summary/e2_ramp.json, summary/e2_devices.csv"""
import csv, json, re, sys
import numpy as np
from multiprocessing import Pool
import hv21, hv2, eh, common as C
import stress as S          # host_v2/scripts/stress.py (read-only): audit_net, top_nodes, LIM
sys.path.insert(0, str(C.CAMP / "scripts"))
import phase2_audit as P2   # read-only: pick()

LIM = S.LIM
OUT = hv21.RAW / "E2"
RAMP0_US = 10.0             # the C2 (v2) ramp: 3.3 V over 10 us


def ramp_us(rate):
    return RAMP0_US / rate


def rtag(rate):
    return f"r{rate:g}".replace(".", "p")


def run(job):
    """One audited run at one ramp rate: power-up + classification (segment 'up'), then power-down + 1 s off ('down')."""
    tag = job["tag"]
    f = OUT / f"{tag}.json"
    if f.exists():
        return json.load(open(f))
    OUT.mkdir(parents=True, exist_ok=True)
    tr = ramp_us(job["rate"])
    wd = C.workdir("hv21_e2")
    net = wd / f"{tag}.cir"
    b = hv2.build_cls(net, job["idx"], vth=0.65, muf=1.0, V1=job["V1"], V2=job["V2"], k=job["k"], prior_state=job["prior_state"])
    hv21.set_powerup_ramp(net, tr)
    nodes = S.top_nodes(net.read_text())
    d, info = hv2.simulate(net, tag, [f"v({n})" for n in nodes], stop_htime_us=b["stop_htime_us"], opts=C.RELAX)
    m, t_read = hv2.metrics_v2(d, b, 0.65)
    devs = S.audit_net(net, d)
    st = hv2.state_at(d, t_read * 1e-6)
    net.unlink()
    netoff = wd / f"{tag}_off.cir"
    eh.build(netoff, 0, inst=False)
    txt = netoff.read_text()
    dn = f"PWL(0 3.3 1u 3.3 {1 + tr:.4g}u 0)"
    txt = re.sub(r"^VDD\s+vdd\s+0\s+.*$", f"VDD vdd 0 {dn}", txt, flags=re.M)
    for i in range(1, 7):
        txt = re.sub(rf"^(VR{i}\s+row{i}\s+0\s+).*$", rf"\g<1>{dn}", txt, flags=re.M)
    for nm, node in (("V_RSTR", "rstr"), ("V_RSTB", "rstb"), ("V_PHIB", "phib")):
        txt = re.sub(rf"^{nm}\s.*$", f"{nm} {node} 0 {dn}", txt, flags=re.M)
    txt = re.sub(r"^V_PHI\s.*$", "V_PHI phi 0 DC 0", txt, flags=re.M)
    txt = re.sub(r"^\.ic .*$", hv2.ic_line(st), txt, flags=re.M)
    txt = re.sub(r"^\.tran .*$", ".tran 100n 1 0 2.5m", txt, flags=re.M)
    netoff.write_text(txt)
    off_nodes = S.top_nodes(txt)
    d2, info2 = hv2.simulate(netoff, tag + "_off", [f"v({n})" for n in off_nodes])
    devs_off = S.audit_net(netoff, d2)
    netoff.unlink()
    src = {"vdd", "rstr", "rstb", "phib", "phi", "hflag", "htime"} | {f"row{i}" for i in range(1, 7)} | {f"rowpre{i}" for i in range(1, 7)}
    internal = [n for n in nodes if n not in src]
    internal_off = [n for n in off_nodes if n not in src]

    def lowest(dd, nn):
        k = min(nn, key=lambda n: float(np.min(dd[f"v({n})"])))
        j = int(np.argmin(dd[f"v({k})"]))
        return dict(node=k, V=float(dd[f"v({k})"][j]), t_us=float(dd["time"][j] * 1e6))
    rec = dict(tag=tag, rate=job["rate"], ramp_us=tr, idx=job["idx"], pick=job["pick"], run=info, run_off=info2,
               outcome=dict(read=m["latched_read"], failure=m["failure_read"], race_us=m["race_us"]), t_read_us=t_read,
               devices=devs, devices_off=devs_off,
               worst=max(devs, key=lambda x: x["max_stress"]), worst_off=max(devs_off, key=lambda x: x["max_stress"]),
               xbar=max((x for x in devs if x["crossbar"]), key=lambda x: x["max_stress"]),
               xbar_off=max((x for x in devs_off if x["crossbar"]), key=lambda x: x["max_stress"]),
               n_above=sum(x["max_stress"] > LIM for x in devs), n_above_off=sum(x["max_stress"] > LIM for x in devs_off),
               lowest=lowest(d, internal), lowest_off=lowest(d2, internal_off), end_state_read=st)
    f.write_text(json.dumps(rec, indent=1, default=float))
    return rec


def start_state(c, rate):
    """Calibration race-b read state -> power-down at this rate -> 1 s off."""
    rb = json.load(open(hv21.CAL / c["key"] / f"{c['key']}_raceb.json"))
    r = hv21.run_idle(f"E2_start_{rtag(rate)}", OUT, rb["end_state_read"], "G", ramp_us=ramp_us(rate))
    return r["end_state"]


def jobs_for(rate, c):
    sel = P2.pick()
    base = dict(V1=c["levels"][0], V2=c["levels"][1], k=c["k"], rate=rate)
    st = start_state(c, rate)
    return [dict(tag=f"E2_{rtag(rate)}_{k}_s{i:02d}", idx=i, pick=k, prior_state=st, **base) for k, i in sel.items()], st, base


def chain_step(rate, c, st, base):
    """#30 at this rate from the start state (classification only, not audited), power-down at this rate + 1 s off,
    then #31 audited (as v2 C2's chained step)."""
    tr = ramp_us(rate)
    m30 = hv21.run_cls(dict(tag=f"E2_{rtag(rate)}_chainprev_s30", idx=30, outdir=OUT, wdir="e2", vth=0.65, muf=1.0,
                            V1=base["V1"], V2=base["V2"], k=base["k"], mode="G", prior_state=st, vth_metric=0.65, ramp_us=tr))
    st2 = hv21.run_idle(f"E2_{rtag(rate)}_chainprev_s30_off", OUT, m30["end_state_read"], "G", ramp_us=tr)["end_state"]
    return dict(tag=f"E2_{rtag(rate)}_chain_s31", idx=31, pick="chain", prior_state=st2, **base)


def summarize():
    import glob
    res = [json.load(open(f)) for f in sorted(glob.glob(str(OUT / "E2_r*_s*.json")))
           if "chainprev" not in f and not f.endswith("_off.json")]
    res = [r for r in res if "devices" in r]
    rows = []
    for r in res:
        for seg, key in (("up", "devices"), ("down", "devices_off")):
            rows += [dict(rate=r["rate"], run=r["tag"], segment=seg, **x) for x in r[key]]
    with open(hv21.SUMM / "e2_devices.csv", "w", newline="") as g:
        w = csv.DictWriter(g, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    out = dict(limit_V=LIM, ramp0_us=RAMP0_US, rates={})
    for rate in sorted({r["rate"] for r in res}):
        rr = [r for r in res if r["rate"] == rate]
        seg = {}
        for s, dk, wk, xk, lk in (("up", "devices", "worst", "xbar", "lowest"), ("down", "devices_off", "worst_off", "xbar_off", "lowest_off")):
            w = max((r[wk] for r in rr), key=lambda x: x["max_stress"])
            wr = max(rr, key=lambda r: r[wk]["max_stress"])
            xb = max((r[xk] for r in rr), key=lambda x: x["max_stress"])
            xr = max(rr, key=lambda r: r[xk]["max_stress"])
            lo = min((r[lk] for r in rr), key=lambda x: x["V"])
            lr = min(rr, key=lambda r: r[lk]["V"])
            n_above = sum(x["max_stress"] > LIM for r in rr for x in r[dk])
            seg[s] = dict(worst=dict(run=wr["tag"], **w), crossbar=dict(run=xr["tag"], **xb), lowest=dict(run=lr["tag"], **lo),
                          n_above=n_above, devices_above=sorted({x["device"] for r in rr for x in r[dk] if x["max_stress"] > LIM}))
        out["rates"][f"{rate:g}"] = dict(ramp_us=rr[0]["ramp_us"], slope_V_per_us=3.3 / rr[0]["ramp_us"], n_runs=len(rr),
                                         outcomes={r["tag"]: r["outcome"] for r in rr}, **seg)
    json.dump(out, open(hv21.SUMM / "e2_ramp.json", "w"), indent=1, default=float)
    return out


if __name__ == "__main__":
    if sys.argv[1] == "summ":
        print(json.dumps(summarize(), indent=1, default=float)[:3000])
        sys.exit()
    import phases21
    c = phases21.cal(0.65)
    assert c["mode"] == "G"
    for rate in [float(a) for a in sys.argv[1:]]:
        js, st, base = jobs_for(rate, c)
        with Pool(4) as p:
            p.map(run, js)
        run(chain_step(rate, c, st, base))
        print("rate", rate, "done", flush=True)
    summarize()
