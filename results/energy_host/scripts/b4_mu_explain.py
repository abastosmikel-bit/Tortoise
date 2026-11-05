"""Why mu x0.5 fails at nominal |V_th| but not at +0.20/+0.35 V with ideal re-trim. Uses only the finished B4 runs
(per-run JSON + 1 us waveforms in raw/b4_aging/); no new simulation. -> summary/b4_mu_explain.json
Per run: rail reset level and rail level at the start of C2 (leading rail), trip level (the first tripper's rail at its
trip; cell median for runs with no trip), voltage to climb in C2 = trip level - leading rail at C2, C2 slope of the
leading rail (first 100 us of C2), race time, lock latency, runner-up gap (time), C1 rail rise."""
import glob, gzip, json
import numpy as np
import eh

T_C2, WINDOW = 507.5, 2500.0
CELLS = {(0.65, 1.0): (1.82, 2.4), (0.65, 0.5): (1.82, 2.4), (0.85, 1.0): (1.62, 2.2), (0.85, 0.5): (1.62, 2.2),
         (1.00, 1.0): (1.47, 2.05), (1.00, 0.5): (1.47, 2.05)}


def wave(f):
    with gzip.open(f, "rt") as g:
        h = g.readline().strip().split(",")
        d = np.loadtxt(g, delimiter=",")
    return {k: d[:, i] for i, k in enumerate(h)}


res = {}
for (v, mu), (V1, V2) in CELLS.items():
    tp = f"G_v{round(v*100):03d}_m{round(mu*100):03d}_L{round(V1*1000):04d}_{round(V2*1000):04d}_s"
    rows = []
    for f in sorted(glob.glob(str(eh.RAW / f"b4_aging/{tp}*.json"))):
        if f.endswith("_draws.json"):
            continue
        m = json.load(open(f))
        w = wave(f.replace(".json", ".csv.gz"))
        t = w["t_us"]
        at = lambda n, x: float(np.interp(x, t, w[n]))
        rc2 = {k: at(f"ap{k}", T_C2) for k in range(1, 6)}
        lead = max(rc2, key=rc2.get)
        slope = (at(f"ap{lead}", T_C2 + 100) - rc2[lead]) / 100 * 1e3          # mV/us
        trip_lvl = None
        if m.get("first"):
            tw = m["trip_us"][str(m["first"])] if str(m["first"]) in m["trip_us"] else m["trip_us"][m["first"]]
            trip_lvl = at(f"ap{m['first']}", tw)
        reset = float(np.mean(list(m["reset_level"].values())))
        rows.append(dict(idx=m["idx"], valid=m.get("valid"), correct=bool(m.get("valid") and m.get("winner") == m["label"]),
                         failure=m.get("failure"), race_us=m.get("race_us"), reset_V=reset, ref_V=m["ref_reset"],
                         lead_at_C2_V=rc2[lead], C1_rise_V=rc2[lead] - reset, trip_V=trip_lvl, slope_mV_us=slope,
                         lock_latency_us=m.get("lock_latency_us"), gap_us=(m.get("gap") or {}).get("gap_reach_us")))
    tl = float(np.median([r["trip_V"] for r in rows if r["trip_V"] is not None]))
    for r in rows:
        tv = r["trip_V"] if r["trip_V"] is not None else tl
        r["climb_V"] = tv - r["lead_at_C2_V"]
        r["race_pred_us"] = r["climb_V"] / (r["slope_mV_us"] * 1e-3) if r["slope_mV_us"] > 0 else None
    med = lambda k, rs=rows: float(np.median([r[k] for r in rs if r[k] is not None])) if any(r[k] is not None for r in rs) else None
    res[f"{v:.2f}_{mu:.2f}"] = dict(
        n=len(rows), correct=sum(r["correct"] for r in rows), valid=sum(bool(r["valid"]) for r in rows),
        failures={f: sum(1 for r in rows if r["failure"] == f) for f in {r["failure"] for r in rows if r["failure"]}},
        median=dict(reset_V=med("reset_V"), ref_V=med("ref_V"), C1_rise_V=med("C1_rise_V"), lead_at_C2_V=med("lead_at_C2_V"),
                    trip_V=tl, climb_V=med("climb_V"), slope_mV_us=med("slope_mV_us"), race_us=med("race_us"),
                    race_pred_us=med("race_pred_us"), lock_latency_us=med("lock_latency_us"), gap_us=med("gap_us")),
        race_pred_max_us=max(r["race_pred_us"] for r in rows if r["race_pred_us"]),
        runs_pred_over_window=sum(1 for r in rows if r["race_pred_us"] and r["race_pred_us"] > WINDOW),
        failed_runs=[dict(idx=r["idx"], failure=r["failure"], race_pred_us=round(r["race_pred_us"], 0) if r["race_pred_us"] else None,
                          race_us=r["race_us"]) for r in rows if not r["valid"]],
        rows=rows)
json.dump(res, open(eh.SUMM / "b4_mu_explain.json", "w"), indent=1, default=float)
for k, c in res.items():
    md = c["median"]
    print(k, f"{c['correct']}/{c['valid']}", c["failures"], {a: round(b, 3) if isinstance(b, float) else b for a, b in md.items()},
          "pred>window", c["runs_pred_over_window"], "pred max", round(c["race_pred_max_us"]))
    print("   failed:", c["failed_runs"])
