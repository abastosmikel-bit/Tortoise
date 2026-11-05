"""Per-phase summaries, recomputed from the per-run JSONs (DECISIONS H3). Usage: python3 summ_phases.py C1|C2|C3|C4|C5|C6|all
-> summary/c1_nominal.json, c1_runs.csv, c3_aging.json, c4_mismatch.json, c5_history.json, c6_lower_edge.json."""
import csv, glob, json, sys
import numpy as np
import hv2, phases as P
from summ import (FC, EHR, block, paired, v1_correct, v2_correct, outcome_v1, outcome_v2, wilson, load)

S = hv2.SUMM
nJ = 1e9


def cal_info(c):
    if c.get("failed"):
        return dict(failed=True)
    return dict(vhat=round(c["vhat"], 5), err_mV=round(c["err_mV"]["a1"], 2) if "err_mV" in c else 0.0,
                mu_hat=round(c["mu_hat"], 4), mu_err_rel=round(c.get("mu_err_rel", 0.0), 4), k=round(c["k"], 4),
                levels=c["levels"], race_t_us=c["race"]["t_us"],
                race_err_mV=round(c["err_mV"]["race"], 2) if c.get("err_mV", {}).get("race") is not None else None,
                flag=c.get("flag", False))


def _gapshift(m, n):
    a, b = (m.get("gap") or {}).get("gap_reach_us"), (n.get("gap") or {}).get("gap_reach_us")
    return round(abs(a - b), 3) if (a is not None and b is not None) else None


def by_idx(runs):
    return {m["idx"]: m for m in runs}


def c1():
    import b1_summary as B1   # energy_host, read-only
    runs = load(hv2.RAW / "C1/C1_v0650_m100_learned_s*.json")
    assert len(runs) == 90, len(runs)
    v1 = load(FC / "raw/v3/phase1/s*.json")
    v1e = load(EHR / "raw/b1_energy/s*.json")
    o12 = load(EHR / "raw/b1_opt_O12/O12_s*.json")
    a, b = by_idx(runs), by_idx(v1)
    rows, changes = [], []
    for i in range(90):
        m, n = a[i], b[i]
        rows.append(dict(idx=i, label=m["label"], v2=outcome_v2(m), v2_correct=v2_correct(m), v1=outcome_v1(n), v1_correct=v1_correct(n),
                         v2_race_us=m.get("race_us"), v1_race_us=round(min(n["trip_us"].values()) - n["tC2_us"], 3) if n.get("trip_us") else None,
                         v2_t_read_us=m.get("t_read_us"), v2_lock_latency_us=m.get("lock_latency_us"),
                         v2_E_nJ=round(B1.tot(m), 2), v2_gap_us=(m.get("gap") or {}).get("gap_reach_us"),
                         v1_gap_us=(n.get("gap") or {}).get("gap_reach_us")))
        if outcome_v2(m) != outcome_v1(n):
            changes.append(rows[-1])
    with open(S / "c1_runs.csv", "w", newline="") as g:
        w = csv.DictWriter(g, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    conf = {lab: {str(k): 0 for k in list(range(1, 6)) + ["invalid"]} for lab in range(1, 6)}
    for m in runs:
        conf[m["label"]][str(m["winner_read"]) if m.get("valid_read") else "invalid"] += 1
    en = B1.energy_block(runs)
    tr = [m["t_read_us"] for m in runs]
    E = [B1.tot(m) for m in runs]
    fit = np.polyfit(tr, E, 1)
    cal = json.load(open(hv2.CAL / "v0650_m100/calibration.json"))
    a1 = json.load(open(hv2.CAL / "v0650_m100/v0650_m100_a1.json"))
    race_E = [float(np.polyval(fit, cal["race"]["t_us"][j] + hv2.timing(cal["k"])["D"] + hv2.timing(cal["k"])["READ"] + 507.7)) for j in (0, 1)]
    calE = a1["E_VDD_nJ"] + sum(race_E)
    # chain
    ch = sorted(load(hv2.RAW / "C1/C1_chain_*_s*.json"), key=lambda m: m["job"]["chain_step"])
    chain = None
    if ch:
        crow = []
        for m in ch:
            ind = a[m["idx"]]
            ts = [abs(m["trip_us"][k] - ind["trip_us"][k]) for k in m["trip_us"] if k in ind["trip_us"]]
            crow.append(dict(step=m["job"]["chain_step"], idx=m["idx"], chain=outcome_v2(m), independent=outcome_v2(ind),
                             max_trip_shift_us=round(max(ts), 3) if ts else None,
                             rail_reset_shift_mV=round(max(abs(m["reset_level"][k] - ind["reset_level"][k]) for k in m["reset_level"]) * 1e3, 3),
                             gap_shift_us=_gapshift(m, ind)))
        chain = dict(n=len(crow), same_outcome=sum(r["chain"] == r["independent"] for r in crow), rows=crow,
                     v1_chain=json.load(open(FC / "summary/v3/chain.json")).get("n_same_outcome"))
    out = dict(v2=block(runs), v1=block(v1, v2=False), paired_v2_vs_v1=paired(a, b), outcome_changes=changes, confusion_v2=conf,
               v1_O12_same_as_v2=sum(outcome_v2(a[m["idx"]]) == outcome_v1(m) for m in o12),
               calibration=cal_info(cal) | dict(note="nominal die = design-time die: estimates equal the design constants by construction"),
               energy_v2=en, energy_v2_vs_t_read=dict(slope_nJ_per_us=round(float(fit[0]), 4), intercept_nJ=round(float(fit[1]), 2),
                                                     r=round(float(np.corrcoef(tr, E)[0, 1]), 4)),
               energy_v1_baseline_nJ=B1.stats([B1.tot(m) for m in v1e]), energy_v1_O12_nJ=B1.stats([B1.tot(m) for m in o12]),
               t_read_us=B1.stats(tr), calibration_session_energy_nJ=dict(a1_VDD=round(a1["E_VDD_nJ"], 1), races_estimated=[round(x, 1) for x in race_E],
                                                                           total=round(calE, 1), note="race energies estimated from the C1 fit E vs t_read (races not instrumented)"),
               energy_per_classification_with_calibration_nJ={str(N): round(float(np.median(E)) + calE / N, 1) for N in (1, 10, 100, 1000, 10000)},
               chain=chain)
    json.dump(out, open(S / "c1_nominal.json", "w"), indent=1, default=float)
    return out


def b4_v1(vth, mu):
    tags = {"none": f"G_v{round(vth*100):03d}_m{round(mu*100):03d}_L1820_2400",
            "ideal": "G_v{:03d}_m{:03d}_L{:04d}_{:04d}".format(round(vth * 100), round(mu * 100), *[round(x * 1000) for x in hv2.eh.formula_levels(vth)])}
    out = {}
    for pol, t in tags.items():
        r = load(EHR / f"raw/b4_aging/{t}_s*.json")
        if len(r) == 20:
            out[pol] = block(r, v2=False)
    return out


def c3():
    cells, rows = {}, []
    for v, m in P.C3_CELLS:
        key = P.ckey(v, m)
        cf = hv2.CAL / key / "calibration.json"
        if not cf.exists():
            continue
        c = json.load(open(cf))
        r = load(hv2.RAW / f"C3/C3_{key}_learned_s*.json")
        ri = load(hv2.RAW / f"C3/C3_{key}_ideal_s*.json")
        cells[f"{v:.2f}_{m:.2f}"] = dict(vth=v, muf=m, calibration=cal_info(c), learned=block(r) if r else None,
                                         ideal=block(ri) if len(ri) == 20 else None, v1=b4_v1(v, m))
    nom = cells.get("0.65_1.00", {}).get("learned")
    fails = []
    if nom and nom["n"] == 20:
        for k, c in cells.items():
            L = c["learned"]
            if c["calibration"].get("failed") or c["calibration"].get("flag") or (L and L["n"] == 20 and L["correct"] <= nom["correct"] - 3):
                fails.append([c["vth"], c["muf"]])
    e11 = load(EHR / "raw/b4_aging/G_v065_m050_L1820_2400_T1340_trace5000_s*.json")
    out = dict(cells=cells, nominal_cell_correct=nom["correct"] if nom else None, failing_cells=fails,
               v1_E11_2_T1x2=block(e11, v2=False) if e11 else None,
               complete=sum(1 for c in cells.values() if c["learned"] and c["learned"]["n"] == 20))
    json.dump(out, open(S / "c3_aging.json", "w"), indent=1, default=float)
    return out


def c4():
    dies = {}
    a_all, b_all = {}, {}
    for d in P.C4_DIES:
        key = P.ckey(0.65, 1.0, d)
        cf = hv2.CAL / key / "calibration.json"
        if not cf.exists():
            continue
        r = load(hv2.RAW / f"C4/C4_{key}_learned_s*.json")
        v1 = load(FC / f"raw/v3/phase3B_V/V_an20_d{d['die']}_s*.json")
        A, B = by_idx(r), by_idx(v1)
        a_all.update({(d["die"], i): x for i, x in A.items()}); b_all.update({(d["die"], i): x for i, x in B.items()})
        dies[d["die"]] = dict(calibration=cal_info(json.load(open(cf))), v2=block(r) if r else None, v1=block(v1, v2=False),
                              paired=paired(A, B) if r else None)
    pool2 = [x for x in a_all.values()]
    out = dict(dies=dies, pooled_v2=block(pool2) if pool2 else None, pooled_v1=block(list(b_all.values()), v2=False),
               pooled_paired=paired(a_all, b_all) if pool2 else None)
    json.dump(out, open(S / "c4_mismatch.json", "w"), indent=1, default=float)
    return out


def c5():
    ind = by_idx(load(hv2.RAW / "C3/C3_v0650_m050_learned_s*.json"))
    out = {}
    for tp in ("v2", "v1reset"):
        ch = sorted(load(hv2.RAW / f"C5/C5_{tp}_*_s*.json"), key=lambda m: m["job"]["chain_step"])
        rows = []
        for m in ch:
            i = ind.get(m["idx"])
            rows.append(dict(step=m["job"]["chain_step"], idx=m["idx"], label=m["label"], chain=outcome_v2(m),
                             independent=outcome_v2(i) if i else None, race_us=m.get("race_us"),
                             race_shift_us=round(m["race_us"] - i["race_us"], 3) if (i and m.get("race_us") and i.get("race_us")) else None,
                             rail_reset_V=round(max(m["reset_level"].values()), 4), ref_reset_V=m.get("ref_reset"),
                             start_rail_V=round(m["prior_state"]["ap1"], 4)))
        out[tp] = dict(n=len(rows), block=block(ch) if ch else None, same_as_independent=sum(r["chain"] == r["independent"] for r in rows), rows=rows)
    out["independent_C3"] = block(list(ind.values())) if ind else None
    json.dump(out, open(S / "c5_history.json", "w"), indent=1, default=float)
    return out


def c6():
    lv = {}
    for v in P.C6_VTH + P.C6B_VTH:
        key = P.ckey(v, 1.0)
        cf = hv2.CAL / key / "calibration.json"
        if not cf.exists():
            continue
        r = load(hv2.RAW / f"C6/C6_{key}_learned_s*.json")
        lv[f"{v:.2f}"] = dict(calibration=cal_info(json.load(open(cf))), v2=block(r) if r else None,
                              na_read_max_losers=round(float(np.median([max(x for k2, x in m["na_read"].items() if int(k2) != m.get("winner_read"))
                                                                        for m in r if m.get("na_read")])), 3) if r else None)
    v1 = {"0.45 fixed (fitc10 3A)": block(load(FC / "raw/v3/phase3A/A_vth045_s*.json"), v2=False),
          "0.55 fixed (fitc10 3A)": block(load(FC / "raw/v3/phase3A/A_vth055_s*.json"), v2=False),
          "0.50 rstb50 (energy/host study E11.1)": block(load(EHR / "raw/b5_full/F_rstb50_v0500_s*.json"), v2=False),
          "0.65 rstb50 (energy/host study E11.1)": block(load(EHR / "raw/b5_full/F_rstb50_v0650_s*.json"), v2=False)}
    out = dict(levels=lv, v1=v1, v1_short_run_threshold=dict(fixed="stuck <= 0.541 V", rstb50="stuck <= 0.477 V (energy/host study B5)"))
    json.dump(out, open(S / "c6_lower_edge.json", "w"), indent=1, default=float)
    return out


if __name__ == "__main__":
    w = sys.argv[1]
    fns = dict(C1=c1, C3=c3, C4=c4, C5=c5, C6=c6)
    for k in (fns if w == "all" else [w]):
        try:
            r = fns[k]()
            print(k, "ok")
        except Exception as e:
            import traceback; traceback.print_exc()
