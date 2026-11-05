"""B3 summary: estimate errors and classification accuracy per method (raw/b3/, summary/b3_estimates.json,
summary/b3_offsets.json) -> summary/b3_methods.json, summary/b3_dies.csv.
Errors are reported against (i) the die's global |V_th| (the quantity the level formula uses) and (ii) the mean
|V_th| of the crossbar banks on that die (global + W-weighted mean of their mismatch draws)."""
import csv, glob, json, re
import numpy as np
import eh, b3_mc as B
import summarize as S

est = json.load(open(B.EST_F))
cls = {}
for f in glob.glob(str(B.OUT / "cls/*.json")):
    if f.endswith("_draws.json"):
        continue
    m = json.load(open(f))
    cls[m["tag"]] = m


def xbar_mean_dvth(key):
    """W-weighted mean DVTH of the crossbar instances X1-X30 for this die (from any classification run's draws)."""
    fs = glob.glob(str(B.OUT / f"cls/M_{key}_*_draws.json"))
    if not fs:
        return None
    dr = json.load(open(fs[0]))
    net = sorted(glob.glob(str(B.OUT / f"cls/M_{key}_*.cir.gz")))[0]
    import gzip
    W = {m.group(1): float(m.group(2)) for m in re.finditer(r"^(X\d+)\s+ap\d\s+row\d\s+vdd\S*\s+potftseg\s+W=(\S+)", gzip.open(net, "rt").read(), re.M)}
    return float(sum(dr[n]["DVTH"] * w for n, w in W.items()) / sum(W.values()))


rows, per = [], {}
for a in B.ANCHORS:
    for d in B.DIES:
        k = f"an{a:02d}_d{d:02d}"
        if k not in est:
            continue
        dd = est[k]["die"]
        xm = xbar_mean_dvth(k)
        for meth in B.METHODS:
            v = dd["g"] if meth == "ideal" else est[k][meth]["vth_est"]
            if v is None:
                rows.append(dict(key=k, anchor=a, die=d, g=dd["g"], method=meth, vth_est=None))
                continue
            V1, V2 = (round(x, 3) for x in eh.formula_levels(v))
            ms = [cls.get(f"M_{k}_L{round(V1*1000):04d}_{round(V2*1000):04d}_s{i:02d}") for i in eh.SUB]
            done = [m for m in ms if m]
            r = dict(key=k, anchor=a, die=d, g=dd["g"], method=meth, vth_est=round(v, 5), err_global_mV=round((v - dd["g"]) * 1e3, 2),
                     err_xbar_mV=round((v - dd["g"] - xm) * 1e3, 2) if xm is not None else None, V1=V1, V2=V2, n=len(done),
                     correct=sum(1 for m in done if m.get("valid") and m.get("winner") == m["label"]),
                     valid=sum(1 for m in done if m.get("valid")),
                     fails=";".join(sorted(S.failure(m) for m in done if not m.get("valid"))))
            rows.append(r)
            per.setdefault((a, meth), []).append(r)
res = dict(offsets=json.load(open(B.OFFS_F)), by_anchor_method={})
for (a, meth), rs in sorted(per.items()):
    e = np.array([r["err_global_mV"] for r in rs])
    ex = np.array([r["err_xbar_mV"] for r in rs if r["err_xbar_mV"] is not None])
    n = sum(r["n"] for r in rs)
    k = sum(r["correct"] for r in rs)
    v = sum(r["valid"] for r in rs)
    res["by_anchor_method"][f"{a}_{meth}"] = dict(
        dies=len(rs), n_runs=n, correct=k, accuracy=round(k / n, 4) if n else None, wilson95=S.wilson(k, n) if n else None,
        valid=v, die_acc_median=float(np.median([r["correct"] / r["n"] for r in rs if r["n"]])) if n else None,
        die_acc_min=float(min(r["correct"] / r["n"] for r in rs if r["n"])) if n else None,
        err_global_mV=dict(mean=round(float(e.mean()), 2), rms=round(float(np.sqrt((e ** 2).mean())), 2), max_abs=round(float(abs(e).max()), 2)),
        err_xbar_mV=dict(mean=round(float(ex.mean()), 2), rms=round(float(np.sqrt((ex ** 2).mean())), 2), max_abs=round(float(abs(ex).max()), 2)) if len(ex) else None,
        missing_estimates=sum(1 for r in rows if r["anchor"] == a and r["method"] == meth and r.get("vth_est") is None))
json.dump(res, open(eh.SUMM / "b3_methods.json", "w"), indent=1)
with open(eh.SUMM / "b3_dies.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["key", "anchor", "die", "g", "method", "vth_est", "err_global_mV", "err_xbar_mV", "V1", "V2",
                                      "n", "correct", "valid", "fails"])
    w.writeheader()
    for r in rows:
        w.writerow(r)
print(json.dumps(res["by_anchor_method"], indent=1))
