"""Variant 1 vs Variant 3 comparison for Phase 1 and Phase 2, from the saved summaries/raw outputs.
-> summary/v1_vs_v3.json"""
import csv, json
import numpy as np
import common as C

S1, S3 = C.CAMP / "summary", C.CAMP / "summary/v3"


def p1(S):
    d = json.load(open(S / "phase1.json")); c = json.load(open(S / "chain.json")); g = d["gap_vs_lock"]
    rr = c["rows"][1:]
    return dict(accuracy=d["accuracy"], accuracy_wilson95=d["accuracy_wilson95"], correct=d["correct"], valid=d["valid"],
                validity=d["validity"], failures=d["failures"], race_time_from_C2_us=d["race_time_from_C2_us"],
                lock_latency_us=g["lock_latency_us"], runner_up_gap_us=g["runner_up_gap_us"],
                margin_gap_minus_latency_us=g["margin_gap_minus_latency_us"], n_valid_gap_below_latency=g["n_gap_below_latency"],
                spice_vs_schemeA_agreement=d["spice_vs_schemeA"]["agreement"], gap_model_vs_spice=d["gap_model_vs_spice"],
                chain_same_outcome=f'{c["n_same_outcome"]}/{c["n"]}',
                chain_max_abs_d_first_trip_us=max(abs(x["d_first_trip_us"]) for x in rr),
                chain_max_abs_d_runner_up_gap_us=max(abs(x["d_runner_up_gap_us"]) for x in rr if x["d_runner_up_gap_us"] is not None),
                chain_max_d_reset_level_mV=max(x["d_reset_level_mV_max"] for x in rr),
                chain_max_abs_d_ref_reset_mV=max(abs(x["d_ref_reset_mV"]) for x in rr))


def p2(S):
    d = json.load(open(S / "phase2_audit.json"))
    return dict(n_devices=d["n_devices"], n_over_limit=d["n_over_limit"], worst=d["worst10"][0]["device"],
                worst_V=d["worst10"][0]["max_stress"], worst_margin_V=d["worst10"][0]["margin_V"],
                crossbar_max_V=d["crossbar"]["max_stress"],
                X80_max_V=max(float(r["max_stress"]) for r in csv.DictReader(open(S / "phase2_devices.csv")) if r["device"] == "X80"))


if __name__ == "__main__":
    r1 = {r["idx"]: r for r in csv.DictReader(open(S1 / "phase1_runs.csv"))}
    r3 = {r["idx"]: r for r in csv.DictReader(open(S3 / "phase1_runs.csv"))}
    same = [i for i in r1 if (r1[i]["spice_class"], r1[i]["valid"]) == (r3[i]["spice_class"], r3[i]["valid"])]
    dg = [abs(float(r1[i]["gap_reach_us"]) - float(r3[i]["gap_reach_us"])) for i in r1 if r1[i]["gap_reach_us"] and r3[i]["gap_reach_us"]]
    rt = [float(r3[i]["trips"].split(";")[0].split(":")[1]) for i in r3 if r3[i]["trips"]]
    d1 = {(r["run"], r["device"]): float(r["max_stress"]) for r in csv.DictReader(open(S1 / "phase2_devices.csv"))}
    d3 = {(r["run"], r["device"]): float(r["max_stress"]) for r in csv.DictReader(open(S3 / "phase2_devices.csv"))}
    dd = {k: d3[k] - d1[k] for k in d1 if k in d3}
    kmax = max(dd, key=lambda k: abs(dd[k]))
    out = dict(phase1=dict(variant1=p1(S1), variant3=p1(S3), n_same_outcome=f"{len(same)}/{len(r1)}",
                           max_abs_runner_up_gap_diff_us=round(max(dg), 4)),
               phase2=dict(variant1=p2(S1), variant3=p2(S3), n_device_runs_compared=len(dd),
                           max_abs_stress_change_V=round(abs(dd[kmax]), 4), at=list(kmax)))
    a1, a3 = json.load(open(S1 / "phase3A.json")), json.load(open(S3 / "phase3A.json"))
    out["phase3A_shared_points"] = {k: dict(variant1=dict(n=a1[k]["n"], accuracy=a1[k]["accuracy"], validity=a1[k]["validity"], failures=a1[k]["failures"],
                                                          race_median_us=a1[k]["race_time_from_C2_us"].get("p50")),
                                            variant3=dict(n=a3[k]["n"], accuracy=a3[k]["accuracy"], validity=a3[k]["validity"], failures=a3[k]["failures"],
                                                          race_median_us=a3[k]["race_time_from_C2_us"].get("p50")))
                                    for k in a1 if a1[k]["n"] > 0}
    (C.CAMP / "summary/v1_vs_v3.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))
