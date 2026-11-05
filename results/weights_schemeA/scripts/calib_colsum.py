"""W13 surrogate check on unequal column sums: weights/probe_le60.npy (column sums 58/60/60/60/58), its own W6 warm
start, 20 K samples (raw/K_probe_le60). The nominal surrogate fitted on K_old (equal sums) predicts these runs; reported
like W4.2. Criterion: W13 as written ("more than 2 disagreements worse than K's 39/40") -> admitted if first_agree >= 17 of 20.
W16.5: K actually had 40/40 winner agreement, so the rule should read ">= 18 of 20"; the check had 20/20 either way.
-> summary/A0_colsum_check.json"""
import json
import numpy as np
import wcommon as W
import surrogate as SG
from calib_fit import agreement

if __name__ == "__main__":
    runs = W.load_runs("K_probe_le60")
    q = SG.corner_params(0.65)
    ag = agreement(runs, q)
    # C2 slope per class vs column sum (the mechanism that is new here)
    F = np.load(W.WEIGHTS / "probe_le60.npy")
    sl = {k: float(np.median([m["c2_slope_mV_per_us"][str(k)] for m in runs if m.get("c2_slope_mV_per_us")])) for k in range(1, 6)}
    out = dict(n=len(runs), colsums=F.sum(0).tolist(), agreement={k: v for k, v in ag.items() if k != "rows"}, rows=ag["rows"],
               c2_slope_median_by_class_mV_per_us=sl,
               slope_ratio_58_over_60=float(np.mean([sl[1], sl[5]]) / np.mean([sl[2], sl[3], sl[4]])), expected_ratio=58 / 60,
               warm_start=json.loads((W.SUMM / "warm_probe_le60.json").read_text()),
               le60_admitted=ag["first_agree"] >= 17)
    (W.SUMM / "A0_colsum_check.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: v for k, v in out.items() if k not in ("rows", "warm_start")}, indent=1, default=float))
    for r in ag["rows"]:
        if r["spice_first"] != r["sur_first"] or r["spice_valid"] != r["sur_valid"]:
            print(r)
