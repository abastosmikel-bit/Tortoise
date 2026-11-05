"""B2 summary from raw/b2_retrim/*.json -> summary/b2_retrim.json, summary/b2_points.csv.
Tolerance band (E4): contiguous offsets around 0 with accuracy >= zero-offset accuracy - 5 points."""
import csv, glob, json, re
import numpy as np
import eh
import summarize as S   # fitc10 campaign: wilson(), failure()

runs = [json.load(open(f)) for f in glob.glob(str(eh.RAW / "b2_retrim/*.json"))]


def key(m):
    v, a, b = re.match(r"R_v(\d+)_a([+-]\d+)_b([+-]\d+)_s", m["tag"]).groups()
    return int(v) / 100, int(a), int(b)


pts = {}
for m in runs:
    pts.setdefault(key(m), []).append(m)


def block(ms):
    n = len(ms)
    k = sum(1 for m in ms if m.get("valid") and m.get("winner") == m["label"])
    v = sum(1 for m in ms if m.get("valid"))
    f = {}
    for m in ms:
        if not m.get("valid"):
            f[S.failure(m)] = f.get(S.failure(m), 0) + 1
    rc = [m["race_us"] for m in ms if m.get("race_us") is not None]
    ks = sum(1 for m in ms if m.get("valid") and m.get("winner") == m["label"] and not m.get("trip_in_C1"))
    return dict(n=n, correct=k, accuracy=round(k / n, 4), wilson95=S.wilson(k, n), valid=v, failures=f, strict_correct=ks,
                trips_in_C1=sum(1 for m in ms if m.get("trip_in_C1")),
                race_median_us=round(float(np.median(rc)), 1) if rc else None, race_max_us=round(float(max(rc)), 1) if rc else None)


def band(curve, nom, tol=0.05):
    """curve: {offset: accuracy}. Contiguous offsets around 0 with accuracy >= nom - tol."""
    offs = sorted(curve)
    ok = lambda o: curve[o] >= nom - tol - 1e-9
    if 0 not in curve or not ok(0):
        return None
    lo = hi = 0
    for o in sorted([o for o in offs if o < 0], reverse=True):
        if ok(o):
            lo = o
        else:
            break
    for o in [o for o in offs if o > 0]:
        if ok(o):
            hi = o
        else:
            break
    return [lo, hi]


res = dict(points={}, bands={})
for v in sorted({k[0] for k in pts}):
    nom = block(pts[(v, 0, 0)])["accuracy"] if (v, 0, 0) in pts and len(pts[(v, 0, 0)]) == 20 else None
    res["bands"][str(v)] = dict(nominal_accuracy=nom)
    for axis, sel in (("V1", lambda k: k[2] == 0), ("V2", lambda k: k[1] == 0), ("diag", lambda k: k[1] == k[2])):
        cur = {}
        for k, ms in pts.items():
            if k[0] == v and sel(k) and len(ms) == 20:
                o = k[1] if axis != "V2" else k[2]
                cur[o] = block(ms)["accuracy"]
        if nom is not None and cur:
            b = band(cur, nom)
            res["bands"][str(v)][axis] = dict(band_mV=b, curve={str(o): a for o, a in sorted(cur.items())})
            if axis == "diag" and b:
                # diagonal offset -delta = host believes |V_th| is delta higher: required |V_th| knowledge
                res["bands"][str(v)]["vth_knowledge_mV"] = dict(overestimate_max=-b[0], underestimate_max=b[1])
for k, ms in sorted(pts.items()):
    res["points"][f"v{k[0]:.2f}_dV1{k[1]:+d}_dV2{k[2]:+d}"] = block(ms)
# joint requirement over both |V_th| points (diagonal): the intersection of the two bands
bs = [res["bands"][v].get("diag", {}).get("band_mV") for v in res["bands"]]
if all(bs) and len(bs) == 2:
    res["vth_knowledge_joint_mV"] = dict(band_diag_mV=[max(b[0] for b in bs), min(b[1] for b in bs)])
json.dump(res, open(eh.SUMM / "b2_retrim.json", "w"), indent=1)
with open(eh.SUMM / "b2_points.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["vth", "dV1_mV", "dV2_mV", "n", "correct", "accuracy", "wilson_lo", "wilson_hi", "valid", "trips_in_C1",
                "race_median_us", "failures"])
    for k, ms in sorted(pts.items()):
        b = block(ms)
        w.writerow([k[0], k[1], k[2], b["n"], b["correct"], b["accuracy"], *b["wilson95"], b["valid"], b["trips_in_C1"],
                    b["race_median_us"], ";".join(f"{a}:{c}" for a, c in b["failures"].items())])
print(json.dumps(res["bands"], indent=1))
