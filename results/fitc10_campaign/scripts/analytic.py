"""Analytic predictions for the 90 test samples (for comparison with SPICE; no SPICE involved).
 * sw: software linear score s = X @ F (HW-trained fingers), winner = argmax.
 * schemeA: rev10/eval/schemeA.py race model, nominal die (no mismatch), used AS-IS - calibrated at the LAB
   corner (VTH 0.85, SS 80 mV/dec, V1 1.62 V), with the build_A protocol T1 = 170 us, V2 = 2.20 V. Not refitted
   to fitc10. Model 'correct' = winner == label and margin to runner-up > 14 us (the model's lock time).
-> summary/analytic.csv"""
import sys, csv
import numpy as np
import common as C
sys.path.insert(0, str(C.W / "eval"))
import schemeA as SA

if __name__ == "__main__":
    X, y = C.XTE, C.YTE
    s = X @ C.F
    dv = np.zeros((1, 6, 5, 60)); dl = np.zeros((1, 5))
    t = SA.trips(C.F, X, dv, dl, 170.0, 2.20)[0]               # N x 5 trip times (us, from C1 start)
    rows = []
    for n in range(len(y)):
        o = np.argsort(t[n]); so = np.argsort(-s[n])
        rows.append(dict(idx=n, label=int(y[n]) + 1, sw_winner=int(so[0]) + 1, sw_score_1=round(float(s[n, so[0]]), 3),
                         sw_score_2=round(float(s[n, so[1]]), 3), sw_runner_up=int(so[1]) + 1,
                         sA_winner=int(o[0]) + 1, sA_runner_up=int(o[1]) + 1, sA_t1_us=round(float(t[n, o[0]]), 2),
                         sA_gap_us=round(float(t[n, o[1]] - t[n, o[0]]), 2),
                         sA_correct=bool(o[0] == y[n] and t[n, o[1]] - t[n, o[0]] > 14.0)))
    with open(C.CAMP / "summary/analytic.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    sw = np.mean([r["sw_winner"] == r["label"] for r in rows]); sa = np.mean([r["sA_winner"] == r["label"] for r in rows])
    sac = np.mean([r["sA_correct"] for r in rows])
    agree = np.mean([r["sw_winner"] == r["sA_winner"] for r in rows])
    print(f"software argmax acc {sw:.4f} | schemeA winner acc {sa:.4f} | schemeA acc incl 14us margin {sac:.4f} | sw-vs-sA agree {agree:.4f}")
    for i in (31, 81): print(rows[i])
