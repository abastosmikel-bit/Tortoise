"""Re-trim corner calibration (DECISIONS.md W4.5) from raw/retrim_old (8 K samples x |V_th| 0.55/0.75/0.85/0.95 V,
re-trimmed host levels, old weights). Per corner: R_k (median reset level per class), alpha and c0 (rail at C2 start vs
C1 drive, all rails), gamma (losers' gap vs rail deficit), and a common trip-level shift dTheta relative to the nominal
per-class Theta_k (median over C2-decided runs of V_w(C2) + s_g (t_trip - t_C2) - Theta_w(0.65)). G_res is kept at the
nominal value (8 runs per corner can't locate it); the near ties seen are reported. Runs that tripped during C1 are
excluded from the Theta fit and used to check the surrogate's C1-trip prediction.
-> summary/surrogate_params.json (corners 0.55..0.95), summary/A0_retrim.json"""
import json
import numpy as np
import wcommon as W
import surrogate as SG
from calib_fit import drive, agreement

if __name__ == "__main__":
    runs = W.load_runs("retrim_old")
    p = json.loads(SG.PFILE.read_text())
    q0 = p["corners"]["0.65"]
    out = {}
    for v in (0.55, 0.75, 0.85, 0.95):
        rs = [m for m in runs if abs(m["levels_vth"] - v) < 1e-9]
        R = np.array([np.median([m["reset_level"][str(k)] for m in rs]) for k in range(1, 6)])
        A, b = [], []
        for m in rs:
            Dk = drive(m["F"], m["x"])
            for k in range(5):
                A.append(Dk[k]); b.append(m["rail_at_C2"][str(k + 1)] - R[k])
        alpha, c0 = np.polyfit(A, b, 1)
        res = np.array(b) - (alpha * np.array(A) + c0)
        dv, gr = [], []
        for m in rs:
            if not m.get("gaps") or m.get("trip_in_C1"):
                continue
            for k, g in m["gaps"].items():
                if g.get("gap_reach_us") is not None:
                    dv.append(m["rail_at_C2"][str(m["first"])] - m["rail_at_C2"][str(k)]); gr.append(g["gap_reach_us"])
        dv, gr = np.array(dv), np.array(gr)
        sl = float(np.sum(dv * gr) / np.sum(gr * gr))
        shifts = [m["rail_at_C2"][str(m["first"])] + sl * (m["trip_us"][str(m["first"])] - m["tC2_us"]) - q0["Theta"][m["first"] - 1]
                  for m in rs if m.get("first") and not m.get("trip_in_C1")]
        dTh = float(np.median(shifts)) if shifts else None
        q = dict(R=R.tolist(), alpha=float(alpha), c0=float(c0), gamma=sl / 60.0,
                 Theta=(np.array(q0["Theta"]) + dTh).tolist(), G_res=q0["G_res"], T1=170.0, WMIN=20.0, V2off=0.25)
        p["corners"][f"{v:.2f}"] = q
        ag = agreement(rs, q)
        out[f"{v:.2f}"] = dict(n=len(rs), params=q, c1_rms_residual_mV=float(np.sqrt(np.mean(res ** 2)) * 1e3),
                               gap_slope_mV_per_us=sl * 1e3, theta_shift_V=dTh, theta_shift_spread_mV=float((max(shifts) - min(shifts)) * 1e3) if shifts else None,
                               window_ref_minus_reset_V=float(np.median([m["ref_reset"] - np.mean(list(m["reset_level"].values())) for m in rs])),
                               trips_in_C1=sum(1 for m in rs if m.get("trip_in_C1")),
                               valid=sum(1 for m in rs if m.get("valid")), failures=[m.get("failure") for m in rs if not m.get("valid")],
                               agreement_in_sample={k: v_ for k, v_ in ag.items() if k != "rows"}, rows=ag["rows"],
                               race_from_C2_us=[round(min(m["trip_us"].values()) - m["tC2_us"], 1) if m.get("trip_us") else None for m in rs])
        # surrogate C1-trip prediction vs SPICE
        pred = []
        for m in rs:
            _, c1 = SG.race(np.array(m["F"]), np.array(m["x"])[None], q)
            pred.append((bool(c1[0, 0]), bool(m.get("trip_in_C1"))))
        out[f"{v:.2f}"]["C1_trip_pred_vs_spice"] = dict(both=sum(a and b for a, b in pred), sur_only=sum(a and not b for a, b in pred),
                                                       spice_only=sum(b and not a for a, b in pred))
    SG.PFILE.write_text(json.dumps(p, indent=1))
    (W.SUMM / "A0_retrim.json").write_text(json.dumps(out, indent=1, default=float))
    for k, v in out.items():
        print(k, {kk: vv for kk, vv in v.items() if kk not in ("rows", "params")})
