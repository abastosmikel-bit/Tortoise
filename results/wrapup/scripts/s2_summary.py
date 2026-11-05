"""Study 2 summary (DECISIONS S2.2-S2.3), recomputed from per-run JSONs -> summary/s2_edge.json, summary/s2_tables.md"""
import json
import numpy as np
import wu
import s2_runs as R
import s2_variants as SV
from s1_summary import block, cal_info, correct, outcome, wilson, mcnemar

PTS = (0.45, 0.47, 0.49, 0.51, 0.65)
REF = {0.49: ("E1", "E1_v0490_m100_v21_s{:02d}", wu.HV21RAW), 0.51: ("E1", "E1_v0510_m100_v21_s{:02d}", wu.HV21RAW),
       0.65: ("C3", "C3_v0650_m100_learned_s{:02d}", wu.HV2RAW)}


def idle_uW(tag):
    f = wu.RAW / "S2idle" / f"{tag}_idle.json"
    return json.load(open(f)).get("P_mean_uW") if f.exists() else None


def main():
    out = dict(variants={}, rev10_1={}, mechanism=json.load(open(wu.SUMM / "s2_mechanism.json"))["0.49"]["median"])
    for v in PTS:
        if v in REF:
            ph, pat, base = REF[v]
            runs = [json.load(open(base / ph / (pat.format(i) + ".json"))) for i in wu.SUB]
            out["rev10_1"][f"{v:.2f}"] = dict(source=f"{base.relative_to(wu.REPO)}/{ph}", **block(runs))
        else:
            out["rev10_1"][f"{v:.2f}"] = dict(source="not run (v2.1); v2 C6 gave 0/20", n=0)
    for var in SV.VARIANTS:
        d = json.load(open(wu.SUMM / f"s2_design_{var}.json"))
        rec = dict(change=SV.VARIANTS[var].note, n_tft=134, design=d, points={})
        for v in PTS:
            key = wu.ckey("S2", v, 1.0, variant=var)
            f = wu.CAL / key / "calibration.json"
            fs = [wu.RAW / "S2" / f"S2_{key}_v21_s{i:02d}.json" for i in wu.SUB]
            if not f.exists() or not all(x.exists() for x in fs):
                rec["points"][f"{v:.2f}"] = dict(status="not run")
                continue
            c = json.load(open(f))
            runs = [json.load(open(x)) for x in fs]
            p = dict(cal=cal_info(c), **block(runs))
            if c.get("mode") == "W":
                P = [idle_uW(r["tag"]) for r in runs]
                P = [x for x in P if x is not None]
                p["standby_uW_median"] = round(float(np.median(P)), 1) if P else None
            if f"{v:.2f}" in out["rev10_1"] and out["rev10_1"][f"{v:.2f}"].get("n"):
                ph, pat, base = REF[v]
                ref = {i: json.load(open(base / ph / (pat.format(i) + ".json"))) for i in wu.SUB}
                A = [correct(r) for r in runs]; B = [correct(ref[i]) for i in wu.SUB]
                b = sum(x and not y for x, y in zip(A, B)); cc = sum(y and not x for x, y in zip(A, B))
                p["paired_vs_rev10_1"] = dict(variant_only=b, rev_only=cc, mcnemar_p=mcnemar(b, cc),
                                              identical_outcomes=sum(outcome(r) == outcome(ref[i]) for r, i in zip(runs, wu.SUB)))
            rec["points"][f"{v:.2f}"] = p
        nom = rec["points"].get("0.65", {})
        rec["nominal_check"] = ("pass" if nom.get("paired_vs_rev10_1", {}).get("identical_outcomes") == 20 else
                                ("fail" if "paired_vs_rev10_1" in nom else "not run"))
        works = [v for v in PTS[:-1] if rec["points"].get(f"{v:.2f}", {}).get("reading") == "works"]
        edge = None
        for v in sorted(PTS[:-1]):
            if all(rec["points"].get(f"{u:.2f}", {}).get("reading") == "works" for u in PTS[:-1] if u >= v):
                edge = v; break
        rec["lower_edge_V"] = edge
        rec["sum_correct_045_051"] = sum(rec["points"].get(f"{v:.2f}", {}).get("correct", 0) for v in PTS[:-1])
        out["variants"][var] = rec
    cands = [v for v, r in out["variants"].items() if r["nominal_check"] == "pass" and r["lower_edge_V"] is not None]
    best = sorted(cands, key=lambda v: (out["variants"][v]["lower_edge_V"], -out["variants"][v]["sum_correct_045_051"],
                                        0 if v == "R10.2-edgeA" else 1))
    out["best"] = best[0] if best else None
    b = out["best"]
    if b:
        key = wu.ckey("S2", 0.65, 1.0, variant=b)
        fs = [(wu.RAW / "S2" / f"S2_{key}_v21_s{i:02d}.json") if i in wu.SUB else (wu.RAW / "S2n90" / f"S2n90_{key}_v21_s{i:02d}.json")
              for i in range(90)]                                     # S2-D1: the 20 subset runs are the nominal-check runs
        if all(x.exists() for x in fs):
            runs = [json.load(open(x)) for x in fs]
            ref = [json.load(open(wu.HV2RAW / "C1" / f"C1_v0650_m100_learned_s{i:02d}.json")) for i in range(90)]
            A = [correct(r) for r in runs]; B = [correct(r) for r in ref]
            bb = sum(x and not y for x, y in zip(A, B)); cc = sum(y and not x for x, y in zip(A, B))
            out["best_nominal90"] = dict(**block(runs), rev10_1=block(ref),
                                         identical_outcomes=sum(outcome(x) == outcome(y) for x, y in zip(runs, ref)),
                                         variant_only=bb, rev_only=cc, mcnemar_p=mcnemar(bb, cc))
        sf = wu.SUMM / f"s2_stress_{b}.json"
        if sf.exists():
            s = json.load(open(sf))
            out["best_stress"] = dict(n_devices=s["n_devices"], n_above=s["n_above_any"], worst=s["worst"]["device"],
                                      worst_V=s["worst"]["max_stress"], crossbar_max_V=s["crossbar_max"]["max_stress"],
                                      min_node_V=s["min_node_V"], min_node_V_off=s["min_node_V_off"])
    json.dump(out, open(wu.SUMM / "s2_edge.json", "w"), indent=1, default=float)
    L = ["| \\|V_th\\| (V) | Tortoise v1.0 (v2.1) correct / valid | " + " | ".join(f"{v}: mode, correct / valid (Wilson 95 %), failures" for v in out["variants"]) + " |",
         "|---|---|" + "---|" * len(out["variants"])]
    for v in PTS:
        r = out["rev10_1"][f"{v:.2f}"]
        row = f"| {v:.2f} | " + (f"{r['correct']} / {r['valid']}" if r.get("n") else "not run") + " | "
        for var, rec in out["variants"].items():
            p = rec["points"].get(f"{v:.2f}", {})
            if "correct" not in p:
                row += "not run | "
                continue
            w = p["accuracy_wilson95"]
            row += (f"{p['cal']['mode']}, **{p['correct']} / {p['valid']}** ({100*w[0]:.1f}–{100*w[1]:.1f} %), "
                    f"{', '.join(f'{a} {b}' for a, b in p['failures'].items()) or '—'} | ")
        L.append(row)
    L.append("")
    for var, rec in out["variants"].items():
        L.append(f"- {var}: nominal check **{rec['nominal_check']}**; lower edge {rec['lower_edge_V']} V; {rec['change']}.")
    (wu.SUMM / "s2_tables.md").write_text("\n".join(L) + "\n")
    print("\n".join(L)); print("best:", out["best"])


if __name__ == "__main__":
    main()
