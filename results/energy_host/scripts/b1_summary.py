"""B1 summary: recomputes every B1 number from the per-run JSONs (raw/b1_energy, raw/b1_opt_*, raw/b1_standby).
-> summary/b1_energy.json, summary/b1_runs.csv"""
import csv, glob, json
import numpy as np
import eh, common as C

PH = ["reset", "calibration", "C1", "C2_race", "post_lock", "total"]
nJ = 1e9


def load(d):
    return [json.load(open(f)) for f in sorted(glob.glob(str(eh.RAW / d / "*.json"))) if not f.endswith("_draws.json")]


def stats(x):
    x = np.asarray([v for v in x if v is not None], float)
    if not len(x):
        return None
    return dict(n=int(len(x)), median=round(float(np.median(x)), 3), min=round(float(x.min()), 3), max=round(float(x.max()), 3),
                p5=round(float(np.percentile(x, 5)), 3), p95=round(float(np.percentile(x, 95)), 3), mean=round(float(x.mean()), 3))


def tot(m, ph="total", kind="net"):
    return sum(v[ph][kind] for v in m["energy"]["source"].values()) * nJ


def blocks5(m, ph="total", kind="net"):
    fine = {}
    for k, v in m["energy"]["block"].items():
        net, blk = k.split(":")
        if net == "vls":
            continue   # internal flow, not a source: reported separately
        fine[blk] = fine.get(blk, 0) + v[ph][kind] * nJ
    return fine, {b5: sum(fine.get(f, 0) for f in fs) for b5, fs in eh.BLOCKS5.items()}


def wilson(k, n):
    import summarize as S
    return S.wilson(k, n)


def acc(runs, key="valid"):
    n = len(runs)
    k = sum(1 for m in runs if m.get("valid") and m.get("winner") == m["label"])
    v = sum(1 for m in runs if m.get("valid"))
    return dict(n=n, correct=k, accuracy=round(k / n, 4), wilson95=wilson(k, n), valid=v, validity=round(v / n, 4))


def energy_block(runs):
    out = dict(total_net_nJ=stats([tot(m) for m in runs]), total_host33_nJ=stats([tot(m, kind="host33") for m in runs]),
               total_pos_nJ=stats([tot(m, kind="pos") for m in runs]))
    out["by_source_net_nJ"] = {s: stats([m["energy"]["source"][s]["total"]["net"] * nJ for m in runs]) for s in eh.SOURCES}
    out["by_source_host33_nJ"] = {s: stats([m["energy"]["source"][s]["total"]["host33"] * nJ for m in runs]) for s in eh.SOURCES}
    out["by_phase_net_nJ"] = {p: stats([tot(m, p) for m in runs]) for p in PH}
    out["phase_duration_us"] = {p: stats([m["energy"]["phases_us"][p][1] - m["energy"]["phases_us"][p][0] for m in runs]) for p in PH}
    f5 = [blocks5(m) for m in runs]
    out["by_block5_net_nJ"] = {b: stats([x[1][b] for x in f5]) for b in eh.BLOCKS5}
    out["by_group_net_nJ"] = {g: stats([x[0].get(g, 0) for x in f5]) for g in sorted({g for x in f5 for g in x[0]})}
    out["by_phase_block5_net_nJ_median"] = {p: {b: round(float(np.median([blocks5(m, p)[1][b] for m in runs])), 3) for b in eh.BLOCKS5}
                                            for p in PH}
    out["vls_to_comparator_senses_nJ"] = stats([m["energy"]["block"]["vls:comp"]["total"]["net"] * nJ for m in runs])
    # mean power per phase (uW): phase energy / phase duration
    out["mean_power_by_phase_uW_median"] = {p: round(float(np.median([tot(m, p) / max(1e-9, (m["energy"]["phases_us"][p][1] -
                                            m["energy"]["phases_us"][p][0])) * 1e3 for m in runs])), 2) for p in PH}
    out["closure_max_rel"] = max(max(m["energy"]["closure_rel"].values()) for m in runs)
    return out


def race_fit(runs):
    x = np.array([m["race_us"] for m in runs if m.get("race_us")])
    y = np.array([tot(m) for m in runs if m.get("race_us")])
    yl = np.array([tot(m, "reset") + tot(m, "calibration") + tot(m, "C1") + tot(m, "C2_race") for m in runs if m.get("race_us")])
    a, b = np.polyfit(x, y, 1)
    a2, b2 = np.polyfit(x, yl, 1)
    return dict(n=int(len(x)), total_vs_race=dict(slope_nJ_per_us=round(float(a), 4), intercept_nJ=round(float(b), 2),
                pearson_r=round(float(np.corrcoef(x, y)[0, 1]), 4)),
                to_lock_vs_race=dict(slope_nJ_per_us=round(float(a2), 4), intercept_nJ=round(float(b2), 2),
                pearson_r=round(float(np.corrcoef(x, yl)[0, 1]), 4)),
                race_us=stats(x))


def compare_phase1(runs):
    p1 = {m["idx"]: m for m in (json.load(open(f)) for f in glob.glob(str(C.RAW / "phase1/s*.json")))}
    same = sum(1 for m in runs if p1[m["idx"]].get("latched") == m.get("latched") and p1[m["idx"]].get("valid") == m.get("valid"))
    dt = []
    for m in runs:
        a, b = p1[m["idx"]].get("trip_us") or {}, m.get("trip_us") or {}
        for k, v in b.items():
            if str(k) in a:
                dt.append(abs(v - a[str(k)]))
    return dict(n=len(runs), same_outcome=same, max_trip_time_diff_us=round(max(dt), 4) if dt else None)


def option(opt, base):
    runs = load(f"b1_opt_{opt}")
    if not runs:
        return None
    bi = {m["idx"]: m for m in base}
    res = dict(accuracy=acc(runs), energy=energy_block(runs))
    out_b = lambda m: m["winner"] if m.get("valid") else None
    res["outcome_changes_vs_baseline"] = [dict(idx=m["idx"], label=m["label"], baseline=out_b(bi[m["idx"]]), option=out_b(m),
                                               failure=m.get("failure")) for m in runs if out_b(m) != out_b(bi[m["idx"]])]
    if "t_cls_us" in runs[0]:
        res["read_state_differs_from_end_state"] = [m["idx"] for m in runs if sorted(m.get("latched_at_cls") or []) != sorted(m.get("latched") or [])]
        res["t_cls_us"] = stats([m["t_cls_us"] for m in runs])
    res["energy_saving_vs_baseline_median_pct"] = round(100 * (1 - res["energy"]["total_net_nJ"]["median"] /
                                                         energy_block(base)["total_net_nJ"]["median"]), 2)
    return res


def standby():
    out = {}
    for f in sorted(glob.glob(str(eh.RAW / "b1_standby/*.json"))):
        r = json.load(open(f))
        out[r["tag"]] = dict(latched_src=r.get("latched_src"), steady=r.get("steady"),
                             steady_rel_change_last_decade=r.get("steady_rel_change_last_decade"),
                             P_total_uW_at=r.get("P_total_uW_at"), P_stageA_end_uW=r.get("P_total_uW_stageA_end"),
                             P_block_uW_end={k: round(v, 3) for k, v in r.get("P_block_uW_end", {}).items() if abs(v) > 1e-3},
                             P_block_uW_start={k: round(v, 3) for k, v in r.get("P_block_uW_start", {}).items() if abs(v) > 1e-3},
                             E_stageA_2ms_nJ=r.get("E_stageA_2ms_nJ"), E_stageB_nJ=r.get("E_stageB_nJ"))
    return out


def idle_energy_nJ(idle_s, tag="s00"):
    """Standby energy over idle_s seconds after a classification (VDD on, idle levels): stage A (first 2 ms, row return,
    exact integral) + stage B power trace (log-spaced, trapezoid). Only valid for idle_s >= 2 ms or 0."""
    r = json.load(open(eh.RAW / f"b1_standby/{tag}.json"))
    if idle_s <= 0:
        return 0.0
    if idle_s <= 2e-3:
        return r["E_stageA_2ms_nJ"] * idle_s / 2e-3     # (linear share; stage A is ~flat after the row edge)
    t = np.array(r["trace"]["t_s"]); p = np.array(r["trace"]["P_total_uW"]) * 1e-6
    tb = idle_s - 2e-3
    m = t < tb
    tt = np.concatenate([[0.0], t[m], [tb]]); pp = np.concatenate([[p[0]], p[m], [np.interp(tb, t, p)]])
    return r["E_stageA_2ms_nJ"] + float(np.trapezoid(pp, tt)) * 1e9


def period_table(base, opts):
    """Energy per classification when classifications repeat every T (back-to-back = T equal to one classification)."""
    Ts = (3.1e-3, 1e-2, 1e-1, 1.0, 10.0, 100.0)
    Eb = energy_block(base)["total_net_nJ"]["median"]
    tb = 3008e-6
    out = {"baseline_VDD_on": {f"{T:g}s": round(Eb + idle_energy_nJ(T - tb), 1) for T in Ts}}
    if opts.get("O1"):
        E1 = opts["O1"]["energy"]["total_net_nJ"]["median"]; t1 = opts["O1"]["t_cls_us"]["median"] * 1e-6
        out["O1_VDD_on"] = {f"{T:g}s": round(E1 + idle_energy_nJ(T - t1), 1) for T in Ts}
    for o in ("O2", "O12"):
        if opts.get(o):
            out[f"{o}_VDD_off_between"] = {f"{T:g}s": opts[o]["energy"]["total_net_nJ"]["median"] for T in Ts}
    out["note"] = ("idle energy from the s00 standby trace (VDD on, idle levels); O1 uses the same trace (its end state "
                   "differs: approximation); O2/O12 idle at 0 W (VDD off). Medians of the per-sample classification energy.")
    return out


if __name__ == "__main__":
    base = load("b1_energy")
    res = dict(n=len(base), accuracy=acc(base), phase1_identity=compare_phase1(base), energy=energy_block(base),
               race_fit=race_fit(base))
    res["options"] = {o: option(o, base) for o in ("O1", "O2", "O12")}
    ch = eh.SUMM / "b1_opt_O1_chain.json"
    res["O1_chain"] = json.load(open(ch)) if ch.exists() else None
    res["standby"] = standby()
    res["energy_vs_period_nJ"] = period_table(base, res["options"])
    json.dump(res, open(eh.SUMM / "b1_energy.json", "w"), indent=1, default=float)
    with open(eh.SUMM / "b1_runs.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idx", "label", "winner", "valid", "failure", "race_us", "lock_us", "E_total_net_nJ", "E_total_host33_nJ"]
                   + [f"E_{p}_nJ" for p in PH[:-1]] + [f"E_{b}_nJ" for b in eh.BLOCKS5])
        for m in sorted(base, key=lambda m: m["idx"]):
            w.writerow([m["idx"], m["label"], m.get("winner"), m.get("valid"), m.get("failure"), m.get("race_us"), m.get("lock_us"),
                        round(tot(m), 3), round(tot(m, kind="host33"), 3)] + [round(tot(m, p), 3) for p in PH[:-1]]
                       + [round(blocks5(m)[1][b], 3) for b in eh.BLOCKS5])
    print(json.dumps({k: res[k] for k in ("n", "accuracy", "phase1_identity", "race_fit")}, indent=1, default=float))
    print(json.dumps(res["energy"]["total_net_nJ"]), json.dumps(res["energy"]["by_block5_net_nJ"], default=float))
