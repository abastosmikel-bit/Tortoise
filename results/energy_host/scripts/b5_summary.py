"""B5 full-run summary: accuracy / validity / failures per host policy and |V_th| -> summary/b5_full.json"""
import glob, json, re
import eh
import summarize as S

pts = {}
for f in glob.glob(str(eh.RAW / "b5_full/F_*.json")):
    m = json.load(open(f))
    pol, v = re.match(r"F_(.+)_v(\d+)_s\d+", m["tag"]).groups()
    pts.setdefault(pol, {}).setdefault(int(v) / 1000, []).append(m)
res = {}
for pol, d in pts.items():
    res[pol] = {}
    for v, ms in sorted(d.items()):
        n = len(ms); k = sum(1 for m in ms if m.get("valid") and m.get("winner") == m["label"]); nv = sum(1 for m in ms if m.get("valid"))
        fails = {}
        for m in ms:
            if not m.get("valid"):
                fails[S.failure(m)] = fails.get(S.failure(m), 0) + 1
        rc = sorted(m["race_us"] for m in ms if m.get("race_us") is not None)
        res[pol][f"{v:.2f}"] = dict(n=n, correct=k, accuracy=round(k / n, 4), wilson95=S.wilson(k, n), valid=nv, failures=fails,
                                   race_median_us=float(sorted(rc)[len(rc)//2] if len(rc)%2 else (sorted(rc)[len(rc)//2-1]+sorted(rc)[len(rc)//2])/2) if rc else None)
json.dump(res, open(eh.SUMM / "b5_full.json", "w"), indent=1)
for pol, d in res.items():
    print(pol, {v: (x["correct"], x["valid"], x["n"]) for v, x in d.items()})
