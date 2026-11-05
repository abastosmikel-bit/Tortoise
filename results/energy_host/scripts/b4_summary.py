"""B4 summary: accuracy / validity map per trim policy (aging PROXIES) -> summary/b4_aging.json, summary/b4_map.csv"""
import csv, glob, json
import numpy as np
import eh, b4_aging as A
import summarize as S

runs = {}
for f in glob.glob(str(A.OUT / "*.json")):
    m = json.load(open(f)); runs[m["tag"]] = m
est = json.load(open(eh.SUMM / "b4_estimates.json"))
pols = ["none", "ideal"] + [p for p in ("rep", "a1", "a2") if any(f"_L" in t for t in runs)]


def cell(pol, v, mu, **tk):
    V1, V2 = A.levels(pol, v, mu)
    tim = "".join(f"_{k}{x:g}" for k, x in sorted(tk.items()))
    ms = [runs.get(A.tag(v, mu, V1, V2, i, tim)) for i in eh.SUB]
    ms = [m for m in ms if m]
    if len(ms) < 20:
        return None
    k = sum(1 for m in ms if m.get("valid") and m.get("winner") == m["label"]); nv = sum(1 for m in ms if m.get("valid"))
    fails = {}
    for m in ms:
        if not m.get("valid"):
            fails[S.failure(m)] = fails.get(S.failure(m), 0) + 1
    rc = sorted(m["race_us"] for m in ms if m.get("race_us") is not None)
    return dict(V1=V1, V2=V2, correct=k, accuracy=k / 20, valid=nv, failures=fails, trips_in_C1=sum(1 for m in ms if m.get("trip_in_C1")),
                race_median_us=float(np.median(rc)) if rc else None, race_max_us=rc[-1] if rc else None)


res = {}
for pol in ("none", "ideal"):   # E10: method re-trim not run
    mp = {}
    for v, mu in A.CELLS:
        try:
            c = cell(pol, v, mu)
        except Exception:
            c = None
        if c:
            mp[f"{v:.2f}_{mu:.2f}"] = c
    if mp:
        res[pol] = mp
res["estimates"] = {k: {m: round(x[m]["vth_est"] - x["vth"], 5) if x[m]["vth_est"] is not None else None for m in ("rep", "a1", "a2")}
                    for k, x in est.items()}
json.dump(res, open(eh.SUMM / "b4_aging.json", "w"), indent=1)
with open(eh.SUMM / "b4_map.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["policy", "vth", "mu", "V1", "V2", "correct", "valid", "trips_in_C1", "race_median_us", "failures"])
    for pol, mp in res.items():
        if pol == "estimates":
            continue
        for k, c in mp.items():
            v, mu = k.split("_")
            w.writerow([pol, v, mu, c["V1"], c["V2"], c["correct"], c["valid"], c["trips_in_C1"], c["race_median_us"],
                        ";".join(f"{a}:{b}" for a, b in c["failures"].items())])
for pol, mp in res.items():
    if pol == "estimates":
        continue
    print(pol)
    for v in A.DV:
        print("  dV %.2f" % v, [f"{mp.get(f'{0.65+v:.2f}_{mu:.2f}', {}).get('correct', '-')}/{mp.get(f'{0.65+v:.2f}_{mu:.2f}', {}).get('valid', '-')}" for mu in A.MU])
