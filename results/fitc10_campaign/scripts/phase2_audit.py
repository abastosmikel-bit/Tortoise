"""Phase 2: gate-dielectric stress audit at fitc10 (Variant 1, 2500 us window, whole transient from t = 0, i.e.
including the host reset/precharge phase). Five runs chosen from the inputs, not from results:
  maxsum  : largest total input sum(x)            minsum : smallest total input sum(x)
  maxcol  : largest single class-column score x@F  mincol : smallest single class-column score x@F
  chain   : chain step #31 started from the end state of chain step #30 (raw/chain/c30_end)
Every top-level node is saved (ASCII raw, full resolution). For EVERY TFT (crossbar potftseg included)
max |V_GS| and max |V_GD| over the transient are computed from terminal voltages and compared with 3.5 V.
The existing rev10 audit.py is also run on each raw as a cross-check (its stdout is saved).
-> summary/phase2_audit.json, summary/phase2_devices.csv, raw/phase2/<tag>.{json,csv.gz,cir.gz,audit.txt}"""
import csv, gzip, json, re, subprocess, sys
import numpy as np
from multiprocessing import Pool
import common as C

LIM = 3.5
OUT = C.RAW / "phase2"


def pick():
    """If a criterion picks a sample already chosen, the next-ranked sample for that criterion is taken."""
    s = C.XTE @ C.F; tot = C.XTE.sum(1); sel = {}
    order = {"maxsum": np.argsort(-tot), "minsum": np.argsort(tot),
             "maxcol": np.argsort(-s.max(1)), "mincol": np.argsort(s.min(1))}
    for k, o in order.items():
        sel[k] = int(next(i for i in o if int(i) not in sel.values()))
    return sel


def read_raw(path):
    L = open(path, errors="ignore").read().split("\n")
    nv = int([l for l in L if l.startswith("No. Variables")][0].split(":")[1])
    npt = int([l for l in L if l.startswith("No. Points")][0].split(":")[1])
    i0 = L.index("Variables:") + 1; names = [L[i0 + k].split()[1].lower() for k in range(nv)]
    j = L.index("Values:") + 1
    tok = np.array(" ".join(L[j:]).split(), dtype=float).reshape(npt, nv + 1)[:, 1:]
    return {n: tok[:, i] for i, n in enumerate(names)}


def audit_one(job):
    tag = job["tag"]; wd = C.workdir(f"p2_v{job['variant']}")
    m = C.run_one(dict(job, outdir=OUT, wdir="p2", audit=True))
    raw = wd / f"{tag}.raw"; net = wd / f"{tag}.cir"
    col = read_raw(raw); t = col["time"]
    V = lambda n: np.zeros_like(t) if n == "0" else col.get(f"v({n})", col.get(n))
    devs = []
    for l in open(net):
        mm = re.match(r"^(X\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(potft(?:seg)?)\s+W=(\S+)\s+L=(\S+)", l)
        if not mm:
            continue
        name, d, g, s, mod, W, Lc = mm.groups()
        vd, vg, vs = V(d.lower()), V(g.lower()), V(s.lower())
        assert vd is not None and vg is not None and vs is not None, (name, d, g, s)
        gs, gd = np.abs(vg - vs), np.abs(vg - vd); st = np.maximum(gs, gd); k = int(np.argmax(st))
        devs.append(dict(run=tag, device=name, model=mod, crossbar=mod == "potftseg", d=d, g=g, s=s, W=float(W), L=float(Lc),
                         max_vgs=round(float(gs.max()), 4), max_vgd=round(float(gd.max()), 4), max_stress=round(float(st[k]), 4),
                         t_max_us=round(float(t[k] * 1e6), 2), in_reset_phase=bool(t[k] < 312.5e-6),
                         margin_V=round(LIM - float(st[k]), 4), us_above_limit=round(float(np.sum(np.diff(t, prepend=t[0])[st > LIM]) * 1e6), 3)))
    a = subprocess.run([sys.executable, str(C.W / "sim/tools/audit.py"), str(net), str(raw), str(LIM), "15"], capture_output=True, text=True)
    (OUT / f"{tag}.audit.txt").write_text(a.stdout + a.stderr)
    raw.unlink()
    return dict(tag=tag, idx=job["idx"], n_points=len(t), n_nodes=len(col) - 1, devices=devs,
                valid=m.get("valid"), latched=m.get("latched"), audit_py_head=a.stdout.splitlines()[:3])


if __name__ == "__main__":
    sel = pick()
    jobs = [dict(tag=f"aud_{k}_s{i:02d}", idx=i, prior=C.RAW / "warmstart/fitc10_warm", variant=C.VAR) for k, i in sel.items()]
    jobs.append(dict(tag="aud_chain_s31", idx=31, prior=C.RAW / "chain/c30_end", variant=C.VAR))
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 4) as p:
        res = p.map(audit_one, jobs)
    alld = [d for r in res for d in r["devices"]]
    with open(C.SUMM / "phase2_devices.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(alld[0])); w.writeheader(); w.writerows(alld)
    worst = {}
    for d in alld:                                   # worst case per device over the 5 runs
        if d["device"] not in worst or d["max_stress"] > worst[d["device"]]["max_stress"]:
            worst[d["device"]] = d
    wl = sorted(worst.values(), key=lambda d: -d["max_stress"])
    xb = [d for d in wl if d["crossbar"]]
    out = dict(limit_V=LIM, selection=sel, chain_run="#31 from end state of chain #30",
               runs=[dict(tag=r["tag"], idx=r["idx"], n_devices=len(r["devices"]), n_crossbar=sum(d["crossbar"] for d in r["devices"]),
                          max_stress=max(d["max_stress"] for d in r["devices"]), n_over=sum(d["max_stress"] > LIM for d in r["devices"]),
                          n_points=r["n_points"], n_nodes=r["n_nodes"], valid=r["valid"], latched=r["latched"], audit_py=r["audit_py_head"]) for r in res],
               n_devices=len(wl), n_over_limit=sum(d["max_stress"] > LIM for d in wl), worst10=wl[:10],
               crossbar=dict(n=len(xb), max_stress=xb[0]["max_stress"] if xb else None, worst=xb[:3], old_analytic_bound_V=2.3))
    (C.SUMM / "phase2_audit.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: v for k, v in out.items() if k != "worst10"}, indent=1, default=float)[:3000])
    for d in wl[:10]:
        print(d)
