#!/usr/bin/env python3
"""Check RESULTS_INDEX.md against the committed summary files.

For every row of the index table (identified by its ID), this script reads the summary file named in the row,
recomputes or reads the numbers that the row's Value, N and "CI or range" cells show, and compares them number by
number. A shown number matches when the summary value, rounded to the shown number of decimals, equals it
(|summary - shown| <= half a unit of the last shown digit). Rows in the table that this script does not know, and
entries this script knows that are missing from the table, are both reported as failures.

Usage: python3 tools/check_results_index.py [--index RESULTS_INDEX.md] [--json out.json]
Exit code 0 only if every row matches. Reads files only; nothing is written unless --json is given.
"""
import json, math, pathlib, re, statistics, sys

REPO = pathlib.Path(__file__).resolve().parents[1]
R = REPO / "results"


def J(rel):
    return json.loads((REPO / rel).read_text())


def wil(lo_hi):
    return [100 * lo_hi[0], 100 * lo_hi[1]]


def pct(x):
    return 100 * x


# ------------------------------------------------------------------ entries: id -> (summary file, extractor)
# extractor(summary) -> dict(value=[...], n=[...], ci=[...]) in the order the numbers appear in the table cells.
FC = "results/fitc10_campaign/summary/"
WS = "results/weights_schemeA/summary/"
EH = "results/energy_host/summary/"
H2 = "results/host_v2/summary/"
H21 = "results/host_v21/summary/"
WU = "results/wrapup/summary/"


def fc01(d):
    return dict(value=[d["correct"], d["n"], pct(d["accuracy"])], n=[d["n"]], ci=wil(d["accuracy_wilson95"]))


def fc02(d):
    return dict(value=[d["valid"], d["n"], pct(d["validity"])], n=[d["n"]], ci=wil(d["validity_wilson95"]))


def fc03(d):
    r = d["race_time_from_C2_us"]
    return dict(value=[r["p50"]], n=[d["n"]], ci=[r["p0"], r["p100"]])


def fc04(d):
    g = d["gap_vs_lock"]
    return dict(value=[g["lock_latency_us"]["p50"]], n=[g["n_valid"]], ci=[g["lock_latency_us"]["p0"], g["lock_latency_us"]["p100"]])


def fc05(d):
    g = d["gap_vs_lock"]["runner_up_gap_us"]
    return dict(value=[g["p50"]], n=[d["gap_vs_lock"]["n_valid"]], ci=[g["p0"], g["p100"], g["p5"]])


def fc06(d):
    g = d["gap_model_vs_spice"]
    return dict(value=[g["pearson_r"], g["median_ratio_spice_over_model"]], n=[g["n"]], ci=[])


def fc07(d):
    return dict(value=[d["n_over_limit"], d["n_devices"], d["worst10"][0]["max_stress"], d["crossbar"]["max_stress"]],
                n=[len(d["runs"])], ci=[])


def fc08(d):
    rows = d["rows"]
    return dict(value=[d["n_same_outcome"], d["n"], max(abs(r["d_first_trip_us"]) for r in rows)], n=[d["n"]], ci=[])


def fc09(d):
    return dict(value=[d[k]["correct"] for k in ("vth055", "vth065_mu100 (nominal, = Phase 1 runs)", "vth075")] + [20],
                n=[20], ci=[pct(x) for k in ("vth055", "vth065_mu100 (nominal, = Phase 1 runs)", "vth075")
                            for x in d[k]["accuracy_wilson95"]])


def fc10(d):
    return dict(value=[d[k]["correct"] for k in ("vth045", "vth085", "vth095", "vth105")] + [20], n=[20], ci=[])


def fc11(d):
    return dict(value=[d[k]["correct"] for k in ("mu050", "mu075", "mu125")] + [20], n=[20], ci=[])


def fc12(d):
    ks = ("vth075", "vth085", "vth095", "vth105")
    return dict(value=[d[k]["correct"] for k in ks] + [20] + [d[k]["strict_correct_C2_resolved"] for k in ks],
                n=[20], ci=[])


def fc13(d, a="anchor_20mV"):
    p = d[a]["pooled"]
    return dict(value=[p["correct"], p["n"], p["valid"], p["n"]], n=[p["n"]], ci=wil(p["accuracy_wilson95"]))


def fc15(d):
    return dict(value=[d[k]["pooled"]["correct"] for k in ("sigma_vth_20mV", "sigma_vth_40mV", "sigma_vth_80mV")] + [100],
                n=[100], ci=[])


def fc16(d):
    return dict(value=[d[k]["pooled"]["correct"] for k in ("anchor_20mV", "anchor_35mV", "anchor_50mV")] + [100],
                n=[100], ci=[])


def fc17(d):
    p = d["phase1"]
    a, b = p["n_same_outcome"].split("/")
    return dict(value=[int(a), int(b), p["variant1"]["race_time_from_C2_us"]["p50"], p["variant3"]["race_time_from_C2_us"]["p50"]],
                n=[int(b)], ci=[])


def fc18(d):
    return dict(value=[d["trip_us"], d["lock_latency_us"], int(d["latched"])], n=[1], ci=[])


def ws01(d, k="lr_bias_free"):
    s = d["summary"][k]
    return dict(value=[pct(s["cv_accuracy_mean"]), pct(s["cv_accuracy_sd_over_repeats"])], n=[210],
                ci=[pct(s["cv_accuracy_min_repeat"]), pct(s["cv_accuracy_max_repeat"])])


def ws04(d):
    r = d["results"]
    return dict(value=[r["cand_a"]["correct"], r["cand_a"]["n"], r["old (reference)"]["correct"], r["old (reference)"]["n"]],
                n=[r["cand_a"]["n"]], ci=wil(r["cand_a"]["wilson95"]))


def ws05(d):
    a = d["accuracy"]
    return dict(value=[a["correct"], a["n"], pct(a["value"])], n=[a["n"]], ci=wil(a["wilson95"]))


def ws06(d):
    v, o = d["validity"], d["old_weights"]["validity"]
    return dict(value=[v["valid"], v["n"], o["valid"], o["n"]], n=[v["n"]], ci=wil(v["wilson95"]))


def ws07(d):
    p = d["paired"]
    return dict(value=[p["new_only"], p["old_only"], p["mcnemar_exact_two_sided_p"]], n=[90], ci=[])


def ws08(d, a="anchor_20mV"):
    x = d["3B_V"][a]
    return dict(value=[x["new"]["correct"], x["new"]["n"], x["old"]["correct"], x["old"]["n"], x["paired"]["mcnemar_exact_p"]],
                n=[x["new"]["n"]], ci=wil(x["new"]["wilson95"]))


def ws10(d):
    s = d["agreement_S_heldout"]
    return dict(value=[d["fit"]["G_res"], s["first_agree"], s["n"]], n=[s["n"]], ci=[])


def ws11(d):
    return dict(value=[d["n_over_limit"], d["n_devices"], d["worst10"][0]["max_stress"], d["crossbar"]["max_stress"]],
                n=[len(d["runs"])], ci=[])


def eh01(d):
    e = d["energy"]["total_net_nJ"]
    return dict(value=[e["median"]], n=[e["n"]], ci=[e["min"], e["max"]])


def eh02(d):
    f = d["race_fit"]["to_lock_vs_race"]
    return dict(value=[f["intercept_nJ"], f["slope_nJ_per_us"], f["pearson_r"]], n=[d["race_fit"]["n"]], ci=[])


def eh03(d):
    s = d["standby"]
    single = [v for v in s.values() if len(v["latched_src"]) == 1]
    double = [v for v in s.values() if len(v["latched_src"]) == 2]
    p0 = [v["P_total_uW_at"]["0.0001s"] for v in single]
    pinf = [v["P_total_uW_at"]["100000s"] for v in single]
    return dict(value=[statistics.median(pinf), statistics.median(p0), double[0]["P_total_uW_at"]["100000s"]],
                n=[len(s)], ci=[min(pinf), max(pinf)])


def eh04(d, o="O1"):
    x = d["options"][o]
    e = x["energy"]["total_net_nJ"]
    return dict(value=[e["median"], x["accuracy"]["correct"], x["accuracy"]["n"]], n=[e["n"]], ci=[e["min"], e["max"]])


def eh06(d):
    p = d["energy_vs_period_nJ"]
    return dict(value=[p["baseline_VDD_on"]["1s"] / 1000, p["O12_VDD_off_between"]["1s"] / 1000], n=[90], ci=[])


def eh07(d, v="0.65"):
    b = d["bands"][v]
    return dict(value=b["V1"]["band_mV"] + b["V2"]["band_mV"], n=[20], ci=[])


def eh09(d, a="20"):
    m = d["by_anchor_method"]
    return dict(value=[m[f"{a}_{k}"]["err_global_mV"]["rms"] for k in ("rep", "a1", "a2")], n=[m[f"{a}_rep"]["dies"]],
                ci=[max(m[f"{a}_{k}"]["err_global_mV"]["max_abs"] for k in ("rep", "a1", "a2"))])


def eh11(d):
    return dict(value=[d["none"][f"0.85_{m}"]["correct"] for m in ("1.00", "0.70", "0.50")] + [20], n=[20], ci=[])


def eh12(d):
    return dict(value=[d["ideal"][f"0.85_{m}"]["correct"] for m in ("1.00", "0.70", "0.50")]
                + [d["ideal"][f"1.00_{m}"]["correct"] for m in ("1.00", "0.70", "0.50")] + [20], n=[20], ci=[])


def eh13(d):
    c = d["none"]["0.65_0.50"]
    return dict(value=[c["correct"], 20, c["failures"].get("timeout", 0)], n=[20], ci=[])


def eh14(d):
    t = d["threshold_V"]
    return dict(value=[t["highest_stuck"], t["lowest_working"]], n=[1], ci=[])


def eh16(d):
    r = d["rstb50"]
    return dict(value=[r["0.50"]["correct"], 20, r["0.65"]["correct"], 20], n=[20], ci=[])


def h201(d):
    v = d["v2"]
    return dict(value=[v["correct"], v["n"], pct(v["correct"] / v["n"]), d["paired_v2_vs_v1"]["n"] - len(d["outcome_changes"]),
                       d["paired_v2_vs_v1"]["n"]], n=[v["n"]], ci=wil(v["accuracy_wilson95"]))


def h202(d):
    e = d["energy_v2"]["total_net_nJ"]
    return dict(value=[e["median"]], n=[e["n"]], ci=[e["min"], e["max"]])


def h203(d):
    v = d["v2"]
    return dict(value=[v["race_us_median"]], n=[v["n"]], ci=v["race_us_range"])


def h204(d):
    c = d["chain"]
    return dict(value=[c["same_outcome"], c["n"], max(r["max_trip_shift_us"] for r in c["rows"])], n=[c["n"]], ci=[])


def h205(d):
    runs = d["runs"].values()
    worst = max(r["worst"]["max_stress"] for r in runs)
    return dict(value=[d["n_above_any"], d["n_devices"], worst, d["crossbar_max"]["max_stress"],
                       min(r["min_node_V_off"] for r in runs), min(r["min_node_V"] for r in runs)], n=[len(d["runs"])], ci=[])


def h206(d):
    c = d["cells"].values()
    k = sum(x["learned"]["correct"] for x in c); n = sum(x["learned"]["n"] for x in c)
    v = sum(x["learned"]["valid"] for x in c)
    lo, hi = wilson(k, n)
    return dict(value=[k, n, pct(k / n), v, n, min(x["learned"]["correct"] for x in c), max(x["learned"]["correct"] for x in c), 20],
                n=[n], ci=[pct(lo), pct(hi)])


def h207(d):
    c = [x["calibration"] for x in d["cells"].values()]
    return dict(value=[min(x["err_mV"] for x in c), max(x["err_mV"] for x in c), pct(min(x["mu_err_rel"] for x in c)),
                       pct(max(x["mu_err_rel"] for x in c))], n=[len(c)], ci=[])


def h208(d):
    p, o = d["pooled_v2"], d["pooled_v1"]
    return dict(value=[p["correct"], p["n"], p["valid"], p["n"], o["correct"], o["n"], o["valid"], o["n"]], n=[p["n"]],
                ci=wil(p["accuracy_wilson95"]))


def h209(d):
    return dict(value=[d["v2"]["same_as_independent"], d["v2"]["n"]], n=[d["v2"]["n"]], ci=[])


def h210(d):
    L = d["levels"]
    low = ("0.45", "0.47", "0.49", "0.51", "0.53", "0.55", "0.57")
    return dict(value=[max(L[k]["v2"]["correct"] for k in low), L["0.59"]["v2"]["correct"], L["0.61"]["v2"]["correct"], 20],
                n=[20], ci=[])


def h211(d):
    return dict(value=[d["calibration_session_energy_nJ"]["total"] / 1000], n=[1], ci=[])


def v01(d):
    P = d["points"]
    ks = ("0.51", "0.53", "0.55", "0.57", "0.59", "0.61")
    return dict(value=[P[k]["correct"] for k in ks] + [20] + [P[k]["valid"] for k in ks],
                n=[20], ci=wil(P["0.51"]["acc_wilson"]))


def v02(d):
    p = d["points"]["0.49"]
    return dict(value=[p["correct"], p["n"], p["failures"]["timeout"], p["failures"]["none_latched"]], n=[p["n"]], ci=[])


def v03(d):
    p = d["pooled"]
    return dict(value=[p["v21"], p["n"], p["v2"], p["n"], p["mcnemar_p_unrounded"]], n=[p["n"]], ci=[])


def v04(d):
    P = d["points"]
    w = [P[k]["standby_uW_mean_med"] for k in P if P[k]["cal"]["mode"] == "W"]
    return dict(value=[min(w), max(w), P["0.61"]["E_cls_nJ_med"], P["0.61"]["standby_uW_mean_med"]], n=[20], ci=[])


def v05(d):
    P = d["points"]
    e = [P[k]["E_cls_nJ_med"] for k in ("0.51", "0.53", "0.55", "0.57", "0.59")]
    return dict(value=[min(e), max(e)], n=[20], ci=[])


def v06(d):
    c = d["chain"]
    return dict(value=[c["same_outcome"], c["n"], c["correct"], c["valid"], c["race_shift_abs_max_us"]], n=[c["n"]], ci=[])


def v07(d):
    rates = d["rates"]
    n_above = sum(rates[r][s]["n_above"] for r in rates for s in ("up", "down"))
    worst = max(rates[r][s]["worst"]["max_stress"] for r in rates for s in ("up", "down"))
    ramps = [rates[r]["ramp_us"] for r in rates]
    return dict(value=[n_above, 134, len(rates), worst, rates["10"]["ramp_us"]], n=[rates["1"]["n_runs"]], ci=[min(ramps), max(ramps)])


def v08(d):
    rates = d["rates"]
    return dict(value=[min(rates[r]["down"]["lowest"]["V"] for r in rates), max(rates[r]["down"]["lowest"]["V"] for r in rates),
                       min(rates[r]["up"]["lowest"]["V"] for r in rates)], n=[rates["1"]["n_runs"]], ci=[])


def v09(d):
    f = d["forced"]["0.61_W"]
    return dict(value=[f["correct"], f["n"], f["standby_uW_mean_med"]], n=[f["n"]], ci=[])


# ------------------------------------------------------------------ wrap-up studies (results/wrapup)
def wu40(d):
    m = d["mcu_per_classification_nJ"]
    return dict(value=[m["MSP430FR2433"]["nominal"]["total_nJ"] / 1000, m["MSPM0L1306"]["nominal"]["total_nJ"] / 1000], n=[],
                ci=[m["MSP430FR2433"]["low"]["total_nJ"] / 1000, m["MSP430FR2433"]["high"]["total_nJ"] / 1000,
                    d["sources"]["cycles_assumption"]["low"], d["sources"]["cycles_assumption"]["high"]])


def wu41(d):
    t = d["trace2"]
    return dict(value=[t["system_floor_nJ"] / 1000, d["comparison"]["ratio_trace2_system_floor_over_msp430_nominal"]], n=[],
                ci=[t["die_energy_nJ_median"] / 1000, t["host_floor_during_classification_nJ"]["LPM0_1MHz_timer_only"] / 1000,
                    t["host_busy_us_median"]])


def wu42(d):
    a = d["trace2"]["area"]
    return dict(value=[a["active_mm2_lower_bound"], d["sources"]["MSP430"]["package_mm2"]], n=[a["n_tft"]],
                ci=[a["tft_channel_mm2"], a["capacitor_mm2"]])


def wu43(d):
    s = d["mcu_standby"]
    return dict(value=[s["MSP430FR2433_LPM3_uW"], s["MSP430FR2433_LPM45_uW"], s["MSPM0L1306_standby_uW"]], n=[], ci=[])


def wu20(d):
    a = d["agreement_in_sample"]
    return dict(value=[a["winner"], a["n"], d["fit"]["rms_residual_mV"], d["fit"]["alpha_b_over_alpha"], d["nominal"]["R"][0]],
                n=[a["n"]], ci=[])


def wu21(d):
    c = d["configs"]
    b8, b4 = c[d["finalists"]["b138"]], c[d["finalists"]["b134"]]
    return dict(value=[100 * b8["S3"], 100 * b8["A_nom"], 100 * b4["S3"], 100 * b4["A_nom"]], n=[20], ci=[])


def wu22(d):
    f = d["finalists"]
    return dict(value=[f["S3_le60_m30_b138"]["correct"], f["S3_le60_m30_b138"]["n"], f["S3_le60_m30_b134"]["correct"],
                       f["S3_le60_m30_b134"]["n"], d["reference_old_weights_v1_protocol"]["correct"],
                       d["reference_old_weights_v1_protocol"]["n"]], n=[20], ci=[])


def wu23(d):
    t = d["test"]
    return dict(value=[t["correct"], t["n"], pct(t["correct"] / t["n"]), t["rev10_1"]["correct"], t["rev10_1"]["n"], t["bias_only"], t["rev_only"],
                       t["mcnemar_p"]], n=[t["n"]], ci=wil(t["accuracy_wilson95"]))


def wu24(d):
    t = d["test"]
    return dict(value=[t["valid"], t["n"], t["rev10_1"]["valid"], t["rev10_1"]["n"], t["failures"]["multi_latched"]], n=[t["n"]],
                ci=wil(t["validity_wilson95"]))


def wu25(d):
    m = d["mismatch"]
    return dict(value=[m["correct"], m["n"], m["C4_correct"], m["n"], m["bias_only"], m["c4_only"], m["mcnemar_p"]], n=[m["n"]],
                ci=wil(m["accuracy_wilson95"]))


def wu26(d):
    s = d["stress"]
    return dict(value=[s["n_above"], s["n_devices"], 3.5, s["worst_V"], s["crossbar_max_V"], s["min_node_V_off"]], n=[5], ci=[])


def wu27(d):
    y = d["yield"]
    return dict(value=[d["n_tft"], y["extra_tft"], y["variant"], y["rev10_1"], y["ratio"], d["energy_nJ_median"]], n=[90], ci=[])


def wu28(d):
    p = d["paired_diff_A_nom"]
    return dict(value=[100 * d["nobias"]["A_nom"], 100 * d["bias"]["A_nom"], 100 * p["mean"], 100 * p["sd"], p["splits_bias_better"],
                       p["splits_equal"]], n=[d["splits"]], ci=[])


def wu01(d):
    a = d["aging"]
    ks = ("S1_v0550_m100", "S1_v0550_m070", "S1_v0550_m050")
    return dict(value=[a[k]["correct"] for k in ks] + [20] + [a[k]["valid"] for k in ks], n=[20], ci=wil(a["S1_v0550_m050"]["accuracy_wilson95"]))


def wu02(d):
    a = d["aging"]
    ks = [k for k in a if not k.startswith("S1_v0550")]
    vh = [a[k]["cal"]["vhat"] for k in ks]
    return dict(value=[sum(a[k]["cal"]["mode"] == "G" for k in ks), len(ks), min(a[k]["correct"] for k in ks), max(a[k]["correct"] for k in ks), 20,
                       min(vh), max(vh)], n=[20], ci=[])


def wu03(d):
    c = [r["cal"] for r in d["aging"].values()]
    return dict(value=[min(x["err_mV"] for x in c), max(x["err_mV"] for x in c), min(x["mu_err_pct"] for x in c), max(x["mu_err_pct"] for x in c)],
                n=[len(c)], ci=[])


def wu04(d):
    p = d["mismatch"]["pooled"]
    return dict(value=[p["correct"], p["n"], p["valid"], p["n"], p["C4"]["correct"], p["C4"]["n"], p["paired_vs_C4"]["only_S1"],
                       p["paired_vs_C4"]["only_C4"], p["paired_vs_C4"]["mcnemar_p"]], n=[p["n"]], ci=wil(p["accuracy_wilson95"]))


def wu05(d):
    a = d["aging"]
    ks = ("S1_v0550_m100", "S1_v0550_m070", "S1_v0550_m050")
    return dict(value=[a[k]["standby_uW_median"] for k in ks] + [a[k]["energy_nJ_median"] for k in ks], n=[20], ci=[])


def wu10(d):
    a, b = d["0.49"], d["0.51"]
    return dict(value=[a["median"]["win_c2p100"], b["median"]["win_c2p100"], a["median"]["lockb_c2p100"], b["median"]["lockb_c2p100"],
                       a["median"]["vsg_lock_c2p100"], b["median"]["vsg_lock_c2p100"], a["median"]["na_lead_max"], b["median"]["na_lead_max"]],
                n=[a["n"]], ci=[])


def wu11(d):
    P = d["variants"]["R10.2-edgeA"]["points"]
    ks = ("0.45", "0.47", "0.49", "0.51", "0.65")
    return dict(value=[P[k]["correct"] for k in ks] + [20, P["0.45"]["failures"]["none_latched"], P["0.65"]["paired_vs_rev10_1"]["identical_outcomes"], 20],
                n=[20], ci=wil(P["0.47"]["accuracy_wilson95"]))


def wu12(d):
    P = d["variants"]["R10.2-edgeB"]["points"]
    ks = ("0.49", "0.51", "0.65")
    return dict(value=[P[k]["correct"] for k in ks] + [20, P["0.65"]["paired_vs_rev10_1"]["identical_outcomes"], 20], n=[20], ci=[])


def wu13(d):
    n = d["best_nominal90"]
    return dict(value=[n["correct"], n["n"], n["valid"], n["n"], n["identical_outcomes"], n["n"], n["energy_nJ_median"]], n=[n["n"]],
                ci=wil(n["accuracy_wilson95"]))


def wu14(d):
    s = d["best_stress"]
    return dict(value=[s["n_above"], s["n_devices"], 3.5, s["worst_V"], s["crossbar_max_V"], s["min_node_V_off"]], n=[5], ci=[])


def wu15(d):
    P = d["variants"]["R10.2-edgeA"]["points"]
    dd = d["variants"]["R10.2-edgeA"]["design"]
    sb = [P[k]["standby_uW_median"] for k in ("0.47", "0.49", "0.51")]
    return dict(value=[1000 * dd["own"]["a1_offset_V"], 1000 * dd["rev10_1"]["a1_offset_V"], dd["own"]["I_ref_uA"], dd["rev10_1"]["I_ref_uA"],
                       min(sb), max(sb)], n=[20], ci=[])


def wilson(k, n, z=1.96):
    p = k / n
    c = 1 + z * z / n
    m = (p + z * z / (2 * n)) / c
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / c
    return m - h, m + h


ENTRIES = {
    "FC-01": (FC + "v3/phase1.json", fc01), "FC-02": (FC + "v3/phase1.json", fc02),
    "FC-03": (FC + "v3/phase1.json", fc03), "FC-04": (FC + "v3/phase1.json", fc04),
    "FC-05": (FC + "v3/phase1.json", fc05), "FC-06": (FC + "v3/phase1.json", fc06),
    "FC-07": (FC + "v3/phase2_audit.json", fc07), "FC-08": (FC + "v3/chain.json", fc08),
    "FC-09": (FC + "v3/phase3A.json", fc09), "FC-10": (FC + "v3/phase3A.json", fc10),
    "FC-11": (FC + "v3/phase3A.json", fc11), "FC-12": (FC + "v3/phase3A_T.json", fc12),
    "FC-13": (FC + "v3/phase3B_V.json", fc13), "FC-14": (FC + "v3/phase3B_V.json", lambda d: fc13(d, "anchor_35mV")),
    "FC-15": (FC + "v3/phase3B.json", fc15), "FC-16": (FC + "v3/phase3B_P.json", fc16),
    "FC-17": (FC + "v1_vs_v3.json", fc17), "FC-18": (FC + "smoke_lab_s81.json", fc18),
    "WS-01": (WS + "A0_ceilings.json", ws01), "WS-02": (WS + "A0_ceilings.json", lambda d: ws01(d, "lr_nobias_eqcol")),
    "WS-03": (WS + "A0_ceilings.json", lambda d: ws01(d, "int_ls")), "WS-04": (WS + "A1_select.json", ws04),
    "WS-05": (WS + "A2_FINAL_frozen.json", ws05), "WS-06": (WS + "A2_FINAL_frozen.json", ws06),
    "WS-07": (WS + "A2_FINAL_frozen.json", ws07), "WS-08": (WS + "A3_FINAL_frozen.json", ws08),
    "WS-09": (WS + "A3_FINAL_frozen.json", lambda d: ws08(d, "anchor_35mV")), "WS-10": (WS + "A0_calibration.json", ws10),
    "WS-11": (WS + "A3_stress_FINAL_frozen.json", ws11),
    "EH-01": (EH + "b1_energy.json", eh01), "EH-02": (EH + "b1_energy.json", eh02), "EH-03": (EH + "b1_energy.json", eh03),
    "EH-04": (EH + "b1_energy.json", eh04), "EH-05": (EH + "b1_energy.json", lambda d: eh04(d, "O12")),
    "EH-06": (EH + "b1_energy.json", eh06), "EH-07": (EH + "b2_retrim.json", eh07),
    "EH-08": (EH + "b2_retrim.json", lambda d: eh07(d, "0.85")), "EH-09": (EH + "b3_methods.json", eh09),
    "EH-10": (EH + "b3_methods.json", lambda d: eh09(d, "35")), "EH-11": (EH + "b4_aging.json", eh11),
    "EH-12": (EH + "b4_aging.json", eh12), "EH-13": (EH + "b4_aging.json", eh13),
    "EH-14": (EH + "b5_short_fixed.json", eh14), "EH-15": (EH + "b5_short_rstb50.json", eh14),
    "EH-16": (EH + "b5_full.json", eh16),
    "H2-01": (H2 + "c1_nominal.json", h201), "H2-02": (H2 + "c1_nominal.json", h202), "H2-03": (H2 + "c1_nominal.json", h203),
    "H2-04": (H2 + "c1_nominal.json", h204), "H2-05": (H2 + "c2_stress.json", h205), "H2-06": (H2 + "c3_aging.json", h206),
    "H2-07": (H2 + "c3_aging.json", h207), "H2-08": (H2 + "c4_mismatch.json", h208), "H2-09": (H2 + "c5_history.json", h209),
    "H2-10": (H2 + "c6_lower_edge.json", h210), "H2-11": (H2 + "c1_nominal.json", h211),
    "V21-01": (H21 + "e1_lower_edge.json", v01), "V21-02": (H21 + "e1_lower_edge.json", v02),
    "V21-03": (H21 + "e1_lower_edge.json", v03), "V21-04": (H21 + "e1_lower_edge.json", v04),
    "V21-05": (H21 + "e1_lower_edge.json", v05), "V21-06": (H21 + "e1_lower_edge.json", v06),
    "V21-07": (H21 + "e2_ramp.json", v07), "V21-08": (H21 + "e2_ramp.json", v08), "V21-09": (H21 + "e1_lower_edge.json", v09),
    "WU-40": (WU + "s4_mcu.json", wu40), "WU-41": (WU + "s4_mcu.json", wu41), "WU-42": (WU + "s4_mcu.json", wu42),
    "WU-43": (WU + "s4_mcu.json", wu43),
    "WU-01": (WU + "s1_modew.json", wu01), "WU-02": (WU + "s1_modew.json", wu02), "WU-03": (WU + "s1_modew.json", wu03),
    "WU-04": (WU + "s1_modew.json", wu04), "WU-05": (WU + "s1_modew.json", wu05),
    "WU-10": (WU + "s2_mechanism.json", wu10), "WU-11": (WU + "s2_edge.json", wu11), "WU-12": (WU + "s2_edge.json", wu12),
    "WU-13": (WU + "s2_edge.json", wu13), "WU-14": (WU + "s2_edge.json", wu14), "WU-15": (WU + "s2_edge.json", wu15),
    "WU-20": (WU + "s3_surrogate_params.json", wu20), "WU-21": (WU + "s3_cv.json", wu21), "WU-22": (WU + "s3_select.json", wu22),
    "WU-23": (WU + "s3_eval.json", wu23), "WU-24": (WU + "s3_eval.json", wu24), "WU-25": (WU + "s3_eval.json", wu25),
    "WU-26": (WU + "s3_eval.json", wu26), "WU-27": (WU + "s3_eval.json", wu27), "WU-28": (WU + "s3_nobias_cv.json", wu28),
}

NUM = re.compile(r"(?<![\w.])[-+−]?\d+(?:\.\d+)?(?:\s*[·x×]\s*10\^?\s*[-−]?\d+|[eE][-−]?\d+)?")


def numbers(cell):
    """Numbers shown in a table cell, as (value, decimals). '1.7·10⁻¹⁸' style is written as 1.7e-18 in the index."""
    out = []
    for m in NUM.finditer(cell.replace("−", "-")):
        s = m.group(0).replace(" ", "")
        mant = re.match(r"[-+]?\d+(?:\.(\d+))?", s)
        dec = len(mant.group(1)) if mant.group(1) else 0
        out.append((float(s), dec, "e" in s.lower()))
    return out


def match(shown, value):
    v, dec, sci = shown
    if sci:   # scientific notation: compare the mantissa at its shown precision
        if value == 0:
            return v == 0
        e = math.floor(math.log10(abs(value)))
        return abs(value / 10 ** e - v / 10 ** e) <= 0.5 * 10 ** -dec + 1e-9
    return abs(value - v) <= 0.5 * 10 ** -dec + 1e-9


def parse_index(path):
    rows = {}
    head = None
    for line in path.read_text().splitlines():
        if not line.startswith("|"):
            head = None if not line.strip() else head
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip()[1:-1])]   # '\|' inside a cell is text
        if cells[0] == "ID":
            head = cells
            continue
        if head is None or set(cells[0]) <= set("-: "):
            continue
        rows[cells[0]] = dict(zip(head, cells))
    return rows


def main():
    args = sys.argv[1:]
    idx = REPO / (args[args.index("--index") + 1] if "--index" in args else "RESULTS_INDEX.md")
    rows = parse_index(idx)
    report, ok_all = [], True
    for rid, (rel, fn) in ENTRIES.items():
        rec = dict(id=rid, file=rel)
        if rid not in rows:
            rec.update(ok=False, problem="missing from the index table")
        else:
            row = rows[rid]
            src = re.search(r"\(([^)]+)\)", row.get("Summary file", ""))
            src_rel = src.group(1) if src else ""
            if src_rel and pathlib.PurePosixPath(src_rel) != pathlib.PurePosixPath(rel):
                rec.update(ok=False, problem=f"index links {src_rel}, checker reads {rel}")
            else:
                exp = fn(J(rel))
                probs = []
                for col, key in (("Value", "value"), ("N", "n"), ("CI or range", "ci")):
                    shown = numbers(row.get(col, ""))
                    want = exp[key]
                    if len(shown) != len(want):
                        probs.append(f"{col}: table shows {len(shown)} numbers {[s[0] for s in shown]}, summary gives {len(want)} {want}")
                        continue
                    for s, w in zip(shown, want):
                        if not match(s, float(w)):
                            probs.append(f"{col}: table {s[0]} vs summary {w}")
                rec.update(ok=not probs, problems=probs, expected=exp)
        ok_all &= rec["ok"]
        report.append(rec)
    for rid in rows:
        if rid not in ENTRIES:
            ok_all = False
            report.append(dict(id=rid, ok=False, problem="row in the index that the checker does not know"))
    for r in report:
        if r["ok"]:
            print(f"  OK   {r['id']:7s} {r['file']}")
        else:
            print(f"  FAIL {r['id']:7s} {r.get('file', '')}  {r.get('problem') or '; '.join(r.get('problems', []))}")
    n_ok = sum(r["ok"] for r in report)
    print(f"{n_ok}/{len(report)} index rows match their summary files" + ("" if ok_all else "  -> MISMATCHES ABOVE"))
    if "--json" in args:
        pathlib.Path(args[args.index("--json") + 1]).write_text(json.dumps(report, indent=1, default=float))
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
