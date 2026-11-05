"""Gate-dielectric stress audit of a candidate variant (DECISIONS S2.3, S3.4): the host_v2 C2 procedure
(results/host_v2/scripts/stress.py, imported read-only; only its output folder is redirected here). Five runs at the
nominal die with the variant's own nominal calibration: maxsum, minsum, maxcol, mincol (fitc10 phase2_audit.pick rule,
column scores of the variant's weights) and #31 after #30 with a power-down + 1 s off; each run audited through
(1) power-up + classification and (2) power-down + 1 s off, ramps at 1x (10 us). Every TFT including the crossbar and
any bias bank: max |V_GS|, |V_GD| vs 3.5 V.
Usage (from s2_runs.py / s3_runs.py): audit(variant, cal, name, score_fn=None) -> summary/<name>.json"""
import csv, json, sys
import numpy as np
import wu, hv2, common as C

sys.path.insert(0, str(wu.REPO / "results/host_v2/scripts"))
import stress as ST           # noqa: E402  (read-only)

LIM = 3.5


def picks(scores):
    """phase2_audit.pick() with a given (90, 5) column-score matrix (the next-ranked sample if one is already taken)."""
    tot = C.XTE.sum(1)
    order = {"maxsum": np.argsort(-tot), "minsum": np.argsort(tot),
             "maxcol": np.argsort(-scores.max(1)), "mincol": np.argsort(scores.min(1))}
    sel = {}
    for k, o in order.items():
        sel[k] = int(next(i for i in o if int(i) not in sel.values()))
    return sel


def _run(job):
    wu.set_context(variant=job.pop("variant"), in_cal=False, die=None)
    return ST.run(job)


def audit(variant, cal, name, scores=None):
    from multiprocessing import Pool
    ST.OUT = wu.RAW / name
    ST.OUT.mkdir(parents=True, exist_ok=True)
    scores = C.XTE @ C.F if scores is None else scores
    sel = picks(scores)
    base = dict(V1=cal["levels"][0], V2=cal["levels"][1], k=cal["k"])
    js = [dict(tag=f"{name}_{k}_s{i:02d}", idx=i, pick=k, prior_state=cal["start_state"], variant=variant, **base) for k, i in sel.items()]
    with Pool(4, maxtasksperchild=1) as p:
        res = p.map(_run, js)
    wu.set_context(variant=variant, in_cal=False, die=None)
    m30 = hv2.run_cls(dict(tag=f"{name}_chainprev_s30", idx=30, outdir=ST.OUT, wdir="wu_stress", V1=base["V1"], V2=base["V2"], k=base["k"],
                           prior_state=cal["start_state"], vth_metric=0.65))
    st = hv2.off_state(f"{name}_chainprev_s30_off", ST.OUT, m30["end_state_read"], 0.65, 1.0, None)
    res.append(_run(dict(tag=f"{name}_chain_s31", idx=31, pick="chain", prior_state=st, variant=variant, **base)))
    alld = [dict(run=r["tag"], phase="classification", **x) for r in res for x in r["devices"]] + \
           [dict(run=r["tag"], phase="power_down_off", **x) for r in res for x in r["devices_off"]]
    with open(wu.SUMM / f"{name}_devices.csv", "w", newline="") as g:
        w = csv.DictWriter(g, fieldnames=list(alld[0]))
        w.writeheader(); w.writerows(alld)
    per_dev = {}
    for x in alld:
        if x["device"] not in per_dev or x["max_stress"] > per_dev[x["device"]]["max_stress"]:
            per_dev[x["device"]] = x
    top = sorted(per_dev.values(), key=lambda x: -x["max_stress"])[:12]
    xb = max((x for x in alld if x["crossbar"]), key=lambda x: x["max_stress"])
    out = dict(variant=variant, limit_V=LIM, picks=sel, n_devices=len(per_dev), n_above_any=sum(x["max_stress"] > LIM for x in per_dev.values()),
               worst=top[0], top=top, crossbar_max=xb, min_node_V=min(r["min_node_V"] for r in res),
               min_node_V_off=min(r["min_node_V_off"] for r in res),
               runs={r["tag"]: dict(pick=r["pick"], idx=r["idx"], outcome=r["outcome"], n_above=r["n_above"], n_above_off=r["n_above_off"],
                                    worst=r["worst"]["device"], worst_V=r["worst"]["max_stress"]) for r in res})
    json.dump(out, open(wu.SUMM / f"{name}.json", "w"), indent=1, default=float)
    print(json.dumps({k: v for k, v in out.items() if k not in ("top", "runs")}, indent=1, default=float))
    return out
