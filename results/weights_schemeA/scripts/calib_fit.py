"""Fit the nominal scheme-A surrogate (DECISIONS.md W4.1) from the calibration runs raw/K_old (old weights, training
samples in K only) and report its agreement with SPICE (W4.2): in-sample on K, 5-fold CV inside K, and on the held-out
selection set S (raw/S_old, if present; S is never used for fitting).
Fitted quantities:
  R_k      rail reset level per class (median over runs; all runs start from the same warm start)
  alpha,c0 rail at C2 start - R_k = alpha * D_k + c0, D_k = sum_i F[i,k] (WMIN + x_i T1)   (all 5 rails of every run)
  s_g      gap slope: SPICE gap_reach of every loser vs its rail deficit at C2 start, gap = dV / s_g
  Theta_k, gamma  winner trip time from C2 = (Theta_k - V_w) / (60 gamma): per-class effective trip level and a common
           average C2 slope s_bar = 60 gamma, least squares with class intercepts
  gap_factor = s_bar / s_g: time differences (gaps, margins) are (t_j - t_k) * gap_factor
  G_res    resolve threshold: SPICE validity vs runner-up gap (logistic fit; bracket reported)
Also reported: lock latency, near-tie failures, C2 slopes, linearity residuals, the gap scale relative to the lab
rev10/eval/schemeA.py model (the campaign's 0.84 analogue), the warm start.
-> summary/surrogate_params.json (nominal part; chain/retrim parts are added by their own fits), summary/A0_calibration.json"""
import json, sys
import numpy as np
import wcommon as W
import surrogate as SG

SPL = json.loads((W.SUMM / "splits.json").read_text())


def drive(F, x, T1=170.0, WMIN=20.0):
    F = np.asarray(F, float); x = np.asarray(x, float)
    return T1 * (x @ F) + WMIN * F.sum(0)


def fit(runs):
    R = np.array([np.median([m["reset_level"][str(k)] for m in runs]) for k in range(1, 6)])
    A, b = [], []
    for m in runs:
        Dk = drive(m["F"], m["x"])
        for k in range(5):
            A.append(Dk[k]); b.append(m["rail_at_C2"][str(k + 1)] - R[k])
    A, b = np.array(A), np.array(b)
    alpha, c0 = np.polyfit(A, b, 1)
    res = b - (alpha * A + c0)
    quad = np.polyfit(A, b, 2)
    # gap slope: every loser's gap_reach vs its rail deficit at C2 start (measured rails)
    dv, gr = [], []
    for m in runs:
        if not m.get("gaps"):
            continue
        w = m["first"]
        for k, g in m["gaps"].items():
            if g.get("gap_reach_us") is None:
                continue
            dv.append(m["rail_at_C2"][str(w)] - m["rail_at_C2"][str(k)]); gr.append(g["gap_reach_us"])
    dv, gr = np.array(dv), np.array(gr)
    sl = np.sum(dv * gr) / np.sum(gr * gr)            # dV = s_g * gap, least squares through 0  -> s_g [V/us]
    # race: winner trip time from C2 = (Theta_k - V_w)/s_bar, per-class Theta_k and a common average slope s_bar, by
    # least squares with class intercepts (per-class medians at s_g would be confounded with race length)
    rows = [(m["first"], m["rail_at_C2"][str(m["first"])], m["trip_us"][str(m["first"])] - m["tC2_us"]) for m in runs if m.get("first")]
    Am = np.zeros((len(rows), 6)); bm = np.zeros(len(rows))
    for j, (k, V, t) in enumerate(rows):
        Am[j, k - 1] = 1.0; Am[j, 5] = -V; bm[j] = t
    xs = np.linalg.lstsq(Am, bm, rcond=None)[0]
    sbar = 1.0 / xs[5]
    wins = np.bincount([k for k, _, _ in rows], minlength=6)[1:]
    Theta = np.where(wins > 0, xs[:5] * sbar, np.nan)
    Theta = np.where(np.isnan(Theta), np.nanmean(Theta), Theta)
    tres = bm - Am @ xs
    gamma = sbar / 60.0
    # resolve threshold
    gv = [((m.get("gap") or {}).get("gap_reach_us"), bool(m.get("valid"))) for m in runs if m.get("gap")]
    G_res, logit = resolve_threshold(gv)
    q = dict(R=R.tolist(), alpha=float(alpha), c0=float(c0), gamma=float(gamma), gap_factor=float(sbar / sl), Theta=Theta.tolist(),
             G_res=float(G_res), T1=170.0, WMIN=20.0, V2off=0.25)
    diag = dict(n_runs=len(runs), c1_fit=dict(n_points=len(A), alpha_V_per_finger_us=float(alpha), c0_V=float(c0),
                                             rms_residual_mV=float(np.sqrt(np.mean(res ** 2)) * 1e3), max_abs_residual_mV=float(np.abs(res).max() * 1e3),
                                             quadratic_coef=quad.tolist(), D_range=[float(A.min()), float(A.max())]),
                gap_slope=dict(n_points=len(dv), slope_mV_per_us=float(sl * 1e3),
                               rms_residual_us=float(np.sqrt(np.mean((gr - dv / sl) ** 2))),
                               rel_residual_median=float(np.median(np.abs(gr - dv / sl) / np.maximum(gr, 1)))),
                race=dict(s_bar_mV_per_us=float(sbar * 1e3), gap_factor=float(sbar / sl), wins_per_class=wins.tolist(),
                          Theta_V=Theta.tolist(), trip_time_rms_residual_us=float(np.sqrt(np.mean(tres ** 2))),
                          trip_time_max_abs_residual_us=float(np.abs(tres).max())),
                resolve=logit)
    return q, diag


def resolve_threshold(gv):
    g = np.array([a for a, _ in gv if a is not None]); v = np.array([b for a, b in gv if a is not None])
    inv = g[~v]; val = g[v]
    lo = float(inv.max()) if len(inv) else None          # largest gap that failed
    hi = float(val.min()) if len(val) else None          # smallest gap that was valid
    # logistic fit valid ~ sigmoid((g - G)/w) by a grid search on the likelihood (w floored at 0.5 us)
    best = None
    for G in np.arange(0.0, 40.0, 0.05):
        for w in (0.5, 1.0, 2.0, 3.0, 5.0):
            p = 1 / (1 + np.exp(-(g - G) / w)); p = np.clip(p, 1e-9, 1 - 1e-9)
            ll = np.sum(np.where(v, np.log(p), np.log(1 - p)))
            if best is None or ll > best[0] + 1e-12:
                best = (ll, G, w)
    overlap = lo is not None and hi is not None and lo > hi
    G_res = best[1] if overlap or lo is None or hi is None else 0.5 * (lo + hi)
    return G_res, dict(n=len(g), n_invalid=int((~v).sum()), largest_failed_gap_us=lo, smallest_valid_gap_us=hi,
                       separable=not overlap, logistic_50pct_us=float(best[1]), logistic_width_us=float(best[2]),
                       G_res_us=float(G_res), rule="midpoint of the bracket if separable, else the logistic 50 % point",
                       invalid_runs=sorted([float(x) for x in inv]))


def agreement(runs, q):
    rows = []
    for m in runs:
        F = np.array(m["F"]); x = np.array(m["x"])[None]; y = np.array([m["label"] - 1])
        w, gap, r, c1 = SG.predict(F, x, q)
        sp_first = m.get("first")
        g = (m.get("gap") or {}).get("gap_reach_us")
        sp_correct = bool(m.get("valid")) and m.get("winner") == m["label"]
        su_valid = bool(gap[0, 0] >= q["G_res"]) and not bool(c1[0, 0])
        su_correct = su_valid and int(w[0, 0]) + 1 == m["label"]
        rows.append(dict(tag=m["tag"], idx=m["idx"], label=m["label"], spice_first=sp_first, spice_valid=bool(m.get("valid")),
                         spice_correct=sp_correct, spice_gap_us=g, spice_runner_up=m.get("runner_up"), failure=m.get("failure"),
                         sur_first=int(w[0, 0]) + 1, sur_runner_up=int(r[0, 0]) + 1, sur_gap_us=round(float(gap[0, 0]), 3),
                         sur_valid=su_valid, sur_correct=su_correct))
    n = len(rows)
    same_ru = [(r["sur_gap_us"], r["spice_gap_us"]) for r in rows if r["spice_gap_us"] is not None and r["sur_runner_up"] == r["spice_runner_up"]
               and r["sur_first"] == r["spice_first"]]
    a, b = (np.array(same_ru).T if same_ru else (np.array([]), np.array([])))
    return dict(n=n, first_agree=sum(r["spice_first"] == r["sur_first"] for r in rows),
                validity_agree=sum(r["spice_valid"] == r["sur_valid"] for r in rows),
                correct_agree=sum(r["spice_correct"] == r["sur_correct"] for r in rows),
                spice_correct=sum(r["spice_correct"] for r in rows), sur_correct=sum(r["sur_correct"] for r in rows),
                gap_pairs=len(same_ru), gap_pearson_r=float(np.corrcoef(a, b)[0, 1]) if len(a) > 2 else None,
                gap_ratio_spice_over_sur_median=float(np.median(b / np.maximum(a, 1e-9))) if len(a) else None,
                gap_abs_err_median_us=float(np.median(np.abs(a - b))) if len(a) else None,
                gap_abs_err_max_us=float(np.max(np.abs(a - b))) if len(a) else None, rows=rows)


def lab_model_ratio(runs):
    """SPICE gap / lab-calibrated rev10/eval/schemeA.py model gap (T1 170, V2 2.20), valid runs, same runner-up."""
    sys.path.insert(0, str(W.REPO / "rev10/eval"))
    import schemeA as SA
    out = []
    for m in runs:
        if not m.get("valid") or not m.get("gap") or m["gap"].get("gap_reach_us") is None:
            continue
        t = SA.trips(np.array(m["F"]), np.array(m["x"])[None], np.zeros((1, 6, 5, 60)), np.zeros((1, 5)), 170.0, 2.20)[0][0]
        o = np.argsort(t)
        if o[0] + 1 == m["first"] and o[1] + 1 == m["runner_up"]:
            out.append((float(t[o[1]] - t[o[0]]), m["gap"]["gap_reach_us"]))
    a, b = np.array(out).T
    return dict(n=len(out), median_ratio=float(np.median(b / a)), pearson_r=float(np.corrcoef(a, b)[0, 1]))


if __name__ == "__main__":
    K = W.load_runs("K_old")
    assert len(K) == 40 and all(m["split"] == "train" and m["idx"] in SPL["K"] for m in K), len(K)
    q, diag = fit(K)
    p = json.loads(SG.PFILE.read_text()) if SG.PFILE.exists() else {}
    p.setdefault("corners", {})["0.65"] = q
    p["nominal_fit"] = dict(source="raw/K_old (40 training runs, old weights)", **{k: q[k] for k in q})
    SG.PFILE.write_text(json.dumps(p, indent=1))
    SG.reload()
    out = dict(fit=q, diagnostics=diag)
    out["lock_latency_us"] = dict(n=sum(1 for m in K if m.get("valid")),
                                  **{f"p{a}": float(np.percentile([m["lock_latency_us"] for m in K if m.get("valid")], a)) for a in (0, 5, 50, 95, 100)})
    out["c2_slope_mV_per_us"] = dict(**{f"p{a}": float(np.percentile([s for m in K for s in m["c2_slope_mV_per_us"].values()], a)) for a in (0, 50, 100)})
    out["race_time_from_C2_us"] = {f"p{a}": float(np.percentile([min(m["trip_us"].values()) - m["tC2_us"] for m in K if m.get("trip_us")], a)) for a in (0, 50, 100)}
    out["near_tie_failures"] = [dict(idx=m["idx"], label=m["label"], failure=m["failure"], latched=m["latched"], first=m["first"],
                                     gap_us=(m.get("gap") or {}).get("gap_reach_us"), trips=m["trip_us"]) for m in K if not m.get("valid")]
    out["trip_in_C1"] = sum(1 for m in K if m.get("trip_in_C1"))
    out["agreement_K_in_sample"] = agreement(K, q)
    # 5-fold CV inside K (fit on 32, predict 8; folds by sorted index, stratified by class order)
    Ks = sorted(K, key=lambda m: (m["label"], m["idx"]))
    cv_rows = []
    for f in range(5):
        te = [m for j, m in enumerate(Ks) if j % 5 == f]; tr = [m for j, m in enumerate(Ks) if j % 5 != f]
        qf, _ = fit(tr)
        cv_rows += agreement(te, qf)["rows"]
    out["agreement_K_cv5"] = dict(n=len(cv_rows), first_agree=sum(r["spice_first"] == r["sur_first"] for r in cv_rows),
                                  validity_agree=sum(r["spice_valid"] == r["sur_valid"] for r in cv_rows),
                                  correct_agree=sum(r["spice_correct"] == r["sur_correct"] for r in cv_rows))
    S = W.load_runs("S_old")
    if S:
        assert all(m["idx"] in SPL["S"] for m in S)
        out["agreement_S_heldout"] = agreement(S, q)
    out["lab_model_gap_ratio_K"] = lab_model_ratio(K)
    out["warm_start"] = json.loads((W.SUMM / "warm_old.json").read_text())
    (W.SUMM / "A0_calibration.json").write_text(json.dumps(out, indent=1, default=float))
    pr = {k: v for k, v in out.items() if k not in ("agreement_K_in_sample", "agreement_S_heldout", "warm_start")}
    print(json.dumps(pr, indent=1, default=float)[:6000])
    for key in ("agreement_K_in_sample", "agreement_S_heldout"):
        if key in out:
            print(key, {k: v for k, v in out[key].items() if k != "rows"})
