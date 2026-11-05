"""Pick the B3 best method by the E8 rule -> summary/b3_best.json"""
import json
import eh
r = json.load(open(eh.SUMM / "b3_methods.json"))["by_anchor_method"]
tot = {}
for k, v in r.items():
    a, m = k.split("_")
    if m == "ideal":
        continue
    t = tot.setdefault(m, dict(correct=0, n=0, sq=0.0, k=0))
    t["correct"] += v["correct"]; t["n"] += v["n_runs"]; t["sq"] += v["err_global_mV"]["rms"] ** 2 * v["dies"]; t["k"] += v["dies"]
for m, t in tot.items():
    t["rms"] = (t["sq"] / t["k"]) ** 0.5
best = max(tot, key=lambda m: tot[m]["correct"])
close = [m for m in tot if tot[best]["correct"] - tot[m]["correct"] <= 2]
if len(close) > 1:
    host = [m for m in close if m in ("a1", "a2")]
    rep_in = "rep" in close
    if rep_in and host:   # tie between the replica and a host-only method: host-only wins (E8)
        close = host
    best = min(close, key=lambda m: tot[m]["rms"])
json.dump(dict(best=best, totals=tot, rule="E8"), open(eh.SUMM / "b3_best.json", "w"), indent=1)
print(best, tot)
