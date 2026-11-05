"""Markdown tables for REPORT.md from summary/*.json. Usage: python3 tables.py C3|C4|C5|C6"""
import json, sys
import hv2, phases as P

S = hv2.SUMM


def cellstr(b, strict=False):
    if not b:
        return "—"
    f = ", ".join(f"{k} {v}" for k, v in sorted(b["failures"].items()))
    s = f"{b['correct']} / {b['valid']}"
    if strict and b.get("trips_in_C1"):
        s += f" (strict {b['strict_correct']})"
    return s + (f" ({f})" if f else "")


def c3():
    d = json.load(open(S / "c3_aging.json"))
    C = d["cells"]
    hdr = "| ΔV_th \\ µ | " + " | ".join(f"×{m:g}" for m in P.MU) + " |\n|---|" + "---|" * len(P.MU)
    out = ["**v2, learned estimates.** Cells: correct / valid of 20 (failures; strict count if trips in C1).", "", hdr]
    for dv in P.DV:
        v = round(0.65 + dv, 2)
        row = [cellstr(C.get(f"{v:.2f}_{m:.2f}", {}).get("learned"), True) for m in P.MU]
        out.append(f"| +{dv:.2f} V ({v:.2f}) | " + " | ".join(row) + " |")
    out += ["", "**Calibration per cell:** |V_th| error (mV) / µ̂ ÷ µ / k / race cross-check error (mV), flag.", "", hdr]
    for dv in P.DV:
        v = round(0.65 + dv, 2)
        row = []
        for m in P.MU:
            c = C.get(f"{v:.2f}_{m:.2f}", {}).get("calibration")
            if not c:
                row.append("—"); continue
            if c.get("failed"):
                row.append("**failed**"); continue
            row.append(f"{c['err_mV']:+.1f} / {c['mu_hat']/m:.3f} / {c['k']:.2f} / {c['race_err_mV']:+.1f}" + (" **FLAG**" if c["flag"] else ""))
        out.append(f"| +{dv:.2f} V | " + " | ".join(row) + " |")
    out += ["", "**Race from C2, median (µs), learned.**", "", hdr]
    for dv in P.DV:
        v = round(0.65 + dv, 2)
        out.append(f"| +{dv:.2f} V | " + " | ".join(str((C.get(f"{v:.2f}_{m:.2f}", {}).get("learned") or {}).get("race_us_median", "—")) for m in P.MU) + " |")
    ideal = [(k, c) for k, c in C.items() if c.get("ideal")]
    if ideal:
        out += ["", "**Ideal-knowledge reference (failing cells only).**", "", "| Cell | learned | ideal |", "|---|---|---|"]
        out += [f"| {c['vth']:.2f} V / ×{c['muf']:g} | {cellstr(c['learned'], True)} | {cellstr(c['ideal'], True)} |" for k, c in ideal]
    out += ["", "**v1 vs v2 on the energy/host study's 3 × 3 cells** (correct / valid of 20).", "",
            "| Cell | v1 no re-trim | v1 ideal re-trim | **v2 learned** |", "|---|---|---|---|"]
    for v in (0.65, 0.85, 1.0):
        for m in (1.0, 0.7, 0.5):
            c = C.get(f"{v:.2f}_{m:.2f}")
            if not c:
                continue
            out.append(f"| {v:.2f} V / ×{m:g} | {cellstr(c['v1'].get('none'))} | {cellstr(c['v1'].get('ideal'))} | {cellstr(c['learned'], True)} |")
    print("\n".join(out))
    print("\nfailing cells:", d["failing_cells"], " nominal cell:", d["nominal_cell_correct"], " complete:", d["complete"])


def c4():
    d = json.load(open(S / "c4_mismatch.json"))
    out = ["| Die (seed) | |V_th| err (mV) / µ̂ / k / flag | v1 3B-V | **v2** | paired: both / v2 only / v1 only / neither (McNemar p) |", "|---|---|---|---|---|"]
    for k, x in d["dies"].items():
        c = x["calibration"]; p = x["paired"] or {}
        out.append(f"| d{k} ({20000+int(k)}) | {c.get('err_mV', 0):+.1f} / {c.get('mu_hat', 0):.3f} / {c.get('k', 0):.2f} / {c.get('flag')} | "
                   f"{cellstr(x['v1'])} | {cellstr(x['v2'], True)} | {p.get('both')} / {p.get('only_first')} / {p.get('only_second')} / {p.get('neither')} ({p.get('mcnemar_p')}) |")
    pv2, pv1, pp = d["pooled_v2"], d["pooled_v1"], d["pooled_paired"]
    out.append(f"| **pooled** | | {pv1['correct']}/{pv1['n']} {pv1['accuracy_wilson95']} valid {pv1['valid']} | {pv2['correct']}/{pv2['n']} {pv2['accuracy_wilson95']} valid {pv2['valid']} | {pp['both']} / {pp['only_first']} / {pp['only_second']} / {pp['neither']} ({pp['mcnemar_p']}) |")
    print("\n".join(out))


def c6():
    d = json.load(open(S / "c6_lower_edge.json"))
    out = ["| |V_th| (V) | V̂ err (mV) / µ̂ / k / flag | V₁/V₂ (V) | **v2** correct / valid | median race (µs) | median highest losing `na` at read (V) |", "|---|---|---|---|---|---|"]
    for k, x in d["levels"].items():
        c = x["calibration"]; b = x["v2"]
        out.append(f"| {k} | {c.get('err_mV', 0):+.1f} / {c.get('mu_hat', 0):.3f} / {c.get('k', 0):.2f} / {c.get('flag')} | {c.get('levels')} | {cellstr(b, True)} | {(b or {}).get('race_us_median')} | {x.get('na_read_max_losers')} |")
    out += ["", "| v1 reference | correct / valid |", "|---|---|"] + [f"| {k} | {cellstr(b)} |" for k, b in d["v1"].items()]
    print("\n".join(out))


def c5():
    d = json.load(open(S / "c5_history.json"))
    print("independent:", cellstr(d["independent_C3"]))
    for tp in ("v2", "v1reset"):
        x = d[tp]
        print(tp, cellstr(x["block"]), "same as independent", x["same_as_independent"], "/", x["n"])
        for r in x["rows"]:
            print("  ", r)


if __name__ == "__main__":
    dict(C3=c3, C4=c4, C5=c5, C6=c6)[sys.argv[1]]()
