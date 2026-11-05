"""A3 stress audit (DECISIONS.md W11) of a frozen weight set: the campaign's Phase 2 procedure
(results/fitc10_campaign/scripts/phase2_audit.py) with the new crossbar. Five runs chosen from the test INPUTS by the
campaign's rule, evaluated with the new weights' column scores (largest/smallest total input, largest/smallest single
column score), plus chain step #31 started from this weight set's chain #30 end state. Every top-level node is saved at
full resolution over the whole transient; every TFT (crossbar included) is checked against 3.5 V; rev10 audit.py is run
as a cross-check.
Usage: python3 stress.py <FINAL_name>      -> summary/A3_stress_<FINAL_name>.json, summary/A3_stress_<FINAL_name>_devices.csv"""
import csv, json, re, subprocess, sys
import numpy as np
from multiprocessing import Pool
import wcommon as W
import runs as R
from eval_test import frozen

sys.path.insert(0, str(W.CAMP / "scripts"))
from phase2_audit import read_raw, LIM      # noqa: E402  (same raw reader and limit as the campaign)


def pick(F):
    s = W.XTE @ F; tot = W.XTE.sum(1); sel = {}
    order = {"maxsum": np.argsort(-tot), "minsum": np.argsort(tot), "maxcol": np.argsort(-s.max(1)), "mincol": np.argsort(s.min(1))}
    for k, o in order.items():
        sel[k] = int(next(i for i in o if int(i) not in sel.values()))
    return sel


def audit_one(job):
    tag = job["tag"]; wd = W.C.workdir(f"{job['wdir']}_v3")
    m = W.run_one(dict(job, audit=True))
    raw = wd / f"{tag}.raw"; net = wd / f"{tag}.cir"
    col = read_raw(raw); t = col["time"]
    V = lambda n: np.zeros_like(t) if n == "0" else col.get(f"v({n})", col.get(n))
    devs = []
    for l in open(net):
        mm = re.match(r"^(X\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(potft(?:seg)?)\s+W=(\S+)\s+L=(\S+)", l)
        if not mm:
            continue
        name, d, g, s, mod, Wd, Lc = mm.groups()
        vd, vg, vs = V(d.lower()), V(g.lower()), V(s.lower())
        gs, gd = np.abs(vg - vs), np.abs(vg - vd); st = np.maximum(gs, gd); k = int(np.argmax(st))
        devs.append(dict(run=tag, device=name, model=mod, crossbar=mod == "potftseg", d=d, g=g, s=s, W=float(Wd), L=float(Lc),
                         max_vgs=round(float(gs.max()), 4), max_vgd=round(float(gd.max()), 4), max_stress=round(float(st[k]), 4),
                         t_max_us=round(float(t[k] * 1e6), 2), in_reset_phase=bool(t[k] < 312.5e-6), margin_V=round(LIM - float(st[k]), 4),
                         us_above_limit=round(float(np.sum(np.diff(t, prepend=t[0])[st > LIM]) * 1e6), 3)))
    a = subprocess.run([sys.executable, str(W.C.W / "sim/tools/audit.py"), str(net), str(raw), str(LIM), "15"], capture_output=True, text=True)
    (job["outdir"] / f"{tag}.audit.txt").write_text(a.stdout + a.stderr)
    raw.unlink(); net.unlink()
    return dict(tag=tag, idx=job["idx"], n_points=len(t), n_nodes=len(col) - 1, devices=devs, valid=m.get("valid"), latched=m.get("latched"),
                audit_py_head=a.stdout.splitlines()[:3])


if __name__ == "__main__":
    name = sys.argv[1]
    F, fro = frozen(name)
    sel = pick(F)
    out = W.RAW / f"A3_{name}/stress"
    prior = W.pathlib.Path(fro["warm_start"])
    base = dict(split="test", F=F, weights_name=name, outdir=out, wdir=f"wsA_stress_{name}", timing=fro.get("timing"))
    jobs = [dict(base, tag=f"aud_{k}_s{i:02d}", idx=i, prior=prior) for k, i in sel.items()]
    jobs.append(dict(base, tag="aud_chain_s31", idx=31, prior=W.RAW / f"chain_{name}/c30_end"))
    out.mkdir(parents=True, exist_ok=True)
    with Pool(4) as p:
        res = p.map(audit_one, jobs)
    alld = [d for r in res for d in r["devices"]]
    with open(W.SUMM / f"A3_stress_{name}_devices.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(alld[0])); w.writeheader(); w.writerows(alld)
    worst = {}
    for d in alld:
        if d["device"] not in worst or d["max_stress"] > worst[d["device"]]["max_stress"]:
            worst[d["device"]] = d
    wl = sorted(worst.values(), key=lambda d: -d["max_stress"])
    xb = [d for d in wl if d["crossbar"]]
    old = json.loads((W.CAMP / "summary/v3/phase2_audit.json").read_text())
    summ = dict(limit_V=LIM, weights=name, selection=sel, chain_run="#31 from this weight set's chain #30 end state",
                runs=[dict(tag=r["tag"], idx=r["idx"], n_devices=len(r["devices"]), n_crossbar=sum(d["crossbar"] for d in r["devices"]),
                           max_stress=max(d["max_stress"] for d in r["devices"]), n_over=sum(d["max_stress"] > LIM for d in r["devices"]),
                           n_points=r["n_points"], valid=r["valid"], latched=r["latched"], audit_py=r["audit_py_head"]) for r in res],
                n_devices=len(wl), n_over_limit=sum(d["max_stress"] > LIM for d in wl), worst10=wl[:10],
                crossbar=dict(n=len(xb), max_stress=xb[0]["max_stress"] if xb else None, worst=xb[:3]),
                old_weights=dict(n_devices=old["n_devices"], n_over_limit=old["n_over_limit"], worst=old["worst10"][0],
                                 crossbar_max=old["crossbar"]["max_stress"], selection=old["selection"]))
    (W.SUMM / f"A3_stress_{name}.json").write_text(json.dumps(summ, indent=1, default=float))
    print(json.dumps({k: v for k, v in summ.items() if k != "worst10"}, indent=1, default=float)[:3000])
