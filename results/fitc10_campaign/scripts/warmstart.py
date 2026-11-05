"""Phase 0.3: fitc10 warm start (DECISIONS.md D7). Repeated #81 runs, Variant 1, 2500 us window; run k starts
from the end state of run k-1 (run 1 from the borrowed lab prior t6L_x2_v085). Stop when every rail reset level
(ap1-5 at 311 us) moves < 5 mV between consecutive runs (max 10 runs). The end state of the last run is the
warm start: raw/warmstart/fitc10_warm.{dat,cols}.  -> summary/warmstart.json"""
import json, shutil
import common as C
from gateB import PRIOR

OUT = C.RAW / "warmstart"
if __name__ == "__main__":
    prior, hist = PRIOR, []
    for k in range(1, 11):
        tag = f"ws{k:02d}_s81"
        m = C.run_one(dict(tag=tag, idx=81, prior=prior, variant=C.VAR, outdir=OUT, wdir="ws", save_prior=OUT / f"{tag}_end"))
        rl = m["reset_level"]
        d = max(abs(rl[i] - hist[-1]["reset_level"][i]) for i in rl) * 1e3 if hist else None
        hist.append(dict(run=k, tag=tag, prior=str(prior), reset_level=rl, ref_reset=m["ref_reset"], max_delta_mV=d,
                         latched=m.get("latched"), valid=m.get("valid"), trip_us=m.get("trip_us"),
                         lock_latency_us=m.get("lock_latency_us"), wall_s=m["run"]["wall_s"]))
        print(json.dumps(hist[-1], default=float), flush=True)
        prior = OUT / f"{tag}_end"
        if d is not None and d < 5.0:
            break
    for ext in (".dat", ".cols"):
        shutil.copy(str(prior) + ext, OUT / f"fitc10_warm{ext}")
    res = dict(converged=hist[-1]["max_delta_mV"] is not None and hist[-1]["max_delta_mV"] < 5.0,
               n_runs=len(hist), warm_start=str(OUT / "fitc10_warm"), runs=hist)
    (C.SUMM / "warmstart.json").write_text(json.dumps(res, indent=1, default=float))
    print("converged", res["converged"], "after", len(hist), "runs")
