"""Summaries for host_v21, recomputed from the per-run JSONs (DECISIONS P3). Usage: python3 summ21.py E1 | E2 | all
-> summary/e1_lower_edge.json, summary/e1_runs.csv, summary/e1_tables.md (E2: stress_ramp.summarize)."""
import csv, json, sys
import numpy as np
import hv21, hv2, eh
import phases21 as P
from summ import wilson, paired, v2_correct, outcome_v2, load   # host_v2/scripts/summ.py, read-only

S = hv21.SUMM
HV2RAW = hv21.HV2 / "raw"


def med(x):
    x = [v for v in x if v is not None]
    return round(float(np.median(x)), 3) if x else None


def rng(x):
    x = [v for v in x if v is not None]
    return [round(float(min(x)), 3), round(float(max(x)), 3)] if x else None


def fails(runs):
    out = {}
    for m in runs:
        f = m.get("failure_read") if "failure_read" in m else "no_data"
        if f:
            out[f] = out.get(f, 0) + 1
    return out


def cal_info(c):
    if c.get("failed"):
        return dict(failed=True, mode=None)
    return dict(mode=c["mode"], forced=c.get("mode_forced", False), vhat=round(c["vhat"], 5), err_mV=round(c["err_mV"]["a1"], 2),
                mu_hat=round(c["mu_hat"], 4), k=round(c["k"], 4), levels=c["levels"], race_t_us=c["race"]["t_us"],
                race_err_mV=round(c["err_mV"]["race"], 2) if c["err_mV"].get("race") is not None else None, flag=c["flag"])


def idle_of(m):
    f = hv21.RAW / "E1idle" / f"{m['tag']}_idle.json"
    return json.load(open(f)) if f.exists() else None


def point(phase, c, v2runs=None):
    runs = [json.load(open(hv21.RAW / phase / f"{phase}_{c['key']}_v21_s{i:02d}.json")) for i in P.SUB
            if (hv21.RAW / phase / f"{phase}_{c['key']}_v21_s{i:02d}.json").exists()]
    n = len(runs)
    corr = sum(v2_correct(m) for m in runs)
    val = sum(bool(m.get("valid_read")) for m in runs)
    idl = [idle_of(m) for m in runs]
    E = [m["energy_nJ"]["total"] for m in runs if "energy_nJ" in m]
    Pm = [x["P_mean_uW"] for x in idl if x and "P_mean_uW" in x]
    Ei = [x["E_idle_nJ"]["total"] for x in idl if x and "E_idle_nJ" in x]
    modes = sorted({m["mode"] for m in runs})
    r = dict(vth=c["vth"], cal=cal_info(c), n=n, modes_of_runs={md: sum(m["mode"] == md for m in runs) for md in modes},
             correct=corr, valid=val, acc_wilson=wilson(corr, n), failures=fails(runs),
             race_med_us=med([m.get("race_us") for m in runs]), t_read_med_us=med([m.get("t_read_us") for m in runs]),
             pre_trip_count_us=rng([m.get("host_timer_pre_trip_us") for m in runs]),
             na_loser_max_read_med=med([sorted(m["na_read"].values())[-2] if m.get("na_read") else None for m in runs]),
             E_cls_nJ_med=med(E), E_cls_nJ_range=rng(E), n_idle=len(Pm),
             standby_uW_mean_med=med(Pm), standby_uW_mean_range=rng(Pm),
             standby_uW_1ms_range=rng([x["P_uW_at"].get("0.001") for x in idl if x and "P_uW_at" in x]),
             standby_uW_1s_range=rng([x["P_uW_at"].get("1") for x in idl if x and "P_uW_at" in x]),
             E_idle_nJ_med=med(Ei),
             E_per_cls_1Hz_nJ_med=med([a + (b["E_idle_nJ"]["total"] if (b and b["mode"] == "W") else 0.0)
                                       for a, b in zip([m["energy_nJ"]["total"] for m in runs], idl)]) if E else None)
    if v2runs is not None:
        a = {m["idx"]: m for m in runs}
        b = {m["idx"]: m for m in v2runs}
        r["v2"] = dict(n=len(v2runs), correct=sum(v2_correct(m) for m in v2runs), valid=sum(bool(m.get("valid_read")) for m in v2runs),
                       failures=fails(v2runs), race_med_us=med([m.get("race_us") for m in v2runs]))
        r["paired_v21_vs_v2"] = paired(a, b, v2_correct, v2_correct)
        r["same_outcome_as_v2"] = sum(outcome_v2(a[k]) == outcome_v2(b[k]) for k in a if k in b)
        r["same_race_as_v2"] = sum(a[k].get("race_us") == b[k].get("race_us") for k in a if k in b)
    return r, runs


def e1():
    out = dict(points={}, forced={}, rows=[])
    rows = []
    allr, allv2 = {}, {}
    for v in P.E1_VTH:
        key = P.ckey(v)
        c = json.load(open(hv21.CAL / key / "calibration.json"))
        v2runs = load(HV2RAW / f"C6/C6_{key}_learned_s*.json")
        r, runs = point("E1", c, v2runs)
        out["points"][f"{v:.2f}"] = r
        for m in runs:
            idl = idle_of(m)
            rows.append(dict(vth=v, idx=m["idx"], label=m["label"], mode=m["mode"], outcome=outcome_v2(m), correct=v2_correct(m),
                             race_us=m.get("race_us"), t_read_us=m.get("t_read_us"), pre_trip_us=m.get("host_timer_pre_trip_us"),
                             E_cls_nJ=round(m["energy_nJ"]["total"], 2) if "energy_nJ" in m else None,
                             standby_mean_uW=round(idl["P_mean_uW"], 2) if idl and "P_mean_uW" in idl else None))
            allr[(v, m["idx"])] = m
        for m in v2runs:
            allv2[(v, m["idx"])] = m
    out["pooled"] = dict(v21=sum(v2_correct(m) for m in allr.values()), v2=sum(v2_correct(m) for m in allv2.values()),
                         n=len(allr), paired=paired(allr, allv2, v2_correct, v2_correct))
    pp = out["pooled"]["paired"]
    import math
    b, c = pp["only_first"], pp["only_second"]
    out["pooled"]["mcnemar_p_unrounded"] = min(1.0, 2 * sum(math.comb(b + c, k) for k in range(min(b, c) + 1)) / 2 ** (b + c))
    for v in P.FORCED_W:
        if not (hv21.CAL / P.ckey(v, forced="W") / "calibration.json").exists():
            continue
        c = json.load(open(hv21.CAL / P.ckey(v, forced="W") / "calibration.json"))
        r, runs = point("E1forced", c, [json.load(open(hv21.RAW / "E1" / f"E1_{P.ckey(v)}_v21_s{i:02d}.json")) for i in P.SUB])
        r["note"] = "paired comparison is against the E1 v2.1 runs at this point (mode G), labelled 'v2' in the keys"
        out["forced"][f"{v:.2f}_W"] = r
    # mode-W chain (P3.3)
    key = P.ckey(P.CHAIN_VTH)
    ch = [json.load(open(f)) for f in sorted((hv21.RAW / "E1chain").glob(f"E1chain_chain_{key}_*_s*.json"))]
    if ch:
        ind = {m["idx"]: json.load(open(hv21.RAW / "E1" / f"E1_{key}_v21_s{m['idx']:02d}.json")) for m in ch}
        sh = [round(m["race_us"] - ind[m["idx"]]["race_us"], 3) for m in ch if m.get("race_us") is not None and ind[m["idx"]].get("race_us") is not None]
        out["chain"] = dict(vth=P.CHAIN_VTH, n=len(ch), mode=sorted({m["mode"] for m in ch}), correct=sum(v2_correct(m) for m in ch),
                            valid=sum(bool(m.get("valid_read")) for m in ch), failures=fails(ch),
                            same_outcome=sum(outcome_v2(m) == outcome_v2(ind[m["idx"]]) for m in ch),
                            changed=[dict(step=m["job"].get("chain_step"), idx=m["idx"], chain=outcome_v2(m), independent=outcome_v2(ind[m["idx"]])) for m in ch
                                     if outcome_v2(m) != outcome_v2(ind[m["idx"]])],
                            race_shift_us=rng(sh), race_shift_abs_max_us=max([abs(x) for x in sh]) if sh else None)
    with open(S / "e1_runs.csv", "w", newline="") as g:
        w = csv.DictWriter(g, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    json.dump(out, open(S / "e1_lower_edge.json", "w"), indent=1, default=float)
    tables(out)
    return out


def ftxt(f):
    return ", ".join(f"{k} {v}" for k, v in sorted(f.items())) if f else ""


def tables(o):
    L = ["**E1: lower-edge sweep, v2.1 vs v2 (N = 20 per point, µ ×1).** v2 = host_v2 C6/C6b runs (imported).", "",
         "| \\|V_th\\| (V) | V̂ (err mV) | mode | **v2.1** correct / valid (failures) | v2 correct / valid (failures) | both / v2.1 only / v2 only / neither (McNemar p) | v2.1 median race (µs) | pre-trip timer count (µs) |",
         "|---|---|---|---|---|---|---|---|"]
    for k, r in o["points"].items():
        c, p = r["cal"], r["paired_v21_vs_v2"]
        L.append(f"| {k} | {c['vhat']:.4f} ({c['err_mV']:+.1f}){' FLAG' if c['flag'] else ''} | {c['mode']} | "
                 f"**{r['correct']} / {r['valid']}**{(' (' + ftxt(r['failures']) + ')') if r['failures'] else ''} | "
                 f"{r['v2']['correct']} / {r['v2']['valid']}{(' (' + ftxt(r['v2']['failures']) + ')') if r['v2']['failures'] else ''} | "
                 f"{p['both']} / {p['only_first']} / {p['only_second']} / {p['neither']} ({p['mcnemar_p']:.3g}) | {r['race_med_us']} | {r['pre_trip_count_us']} |")
    po = o["pooled"]
    L += ["", f"Pooled over the 7 points: v2.1 {po['v21']}/{po['n']}, v2 {po['v2']}/{po['n']}; paired both / v2.1 only / v2 only / neither "
          f"{po['paired']['both']} / {po['paired']['only_first']} / {po['paired']['only_second']} / {po['paired']['neither']} (exact McNemar p = {po['mcnemar_p_unrounded']:.2g}).", "",
          "**Energy and standby per point** (medians over the runs; standby = mean power over the 1 s idle after each run).", "",
          "| \\|V_th\\| (V) | mode | E per classification (nJ) | standby mean (µW), range | standby at 1 ms / 1 s (µW, ranges) | idle energy per 1 s (nJ) | per classification at 1 /s (nJ) |",
          "|---|---|---|---|---|---|---|"]
    for k, r in o["points"].items():
        L.append(f"| {k} | {r['cal']['mode']} | {r['E_cls_nJ_med']} ({r['E_cls_nJ_range']}) | {r['standby_uW_mean_med']} ({r['standby_uW_mean_range']}) | "
                 f"{r['standby_uW_1ms_range']} / {r['standby_uW_1s_range']} | {r['E_idle_nJ_med']} | {r['E_per_cls_1Hz_nJ_med']} |")
    for k, r in o["forced"].items():
        c, p = r["cal"], r["paired_v21_vs_v2"]
        L += ["", f"**Forced mode W at {k[:4]} V** (P3.2): V̂ {c['vhat']:.4f} V, flag {c['flag']}; **{r['correct']} / {r['valid']}** "
              f"({ftxt(r['failures'])}); vs the v2.1 (mode G) runs at the same point: both / W only / G only / neither "
              f"{p['both']} / {p['only_first']} / {p['only_second']} / {p['neither']} (p = {p['mcnemar_p']:.3g}), same outcome {r['same_outcome_as_v2']}/20; "
              f"median race {r['race_med_us']} µs; standby mean {r['standby_uW_mean_med']} µW ({r['standby_uW_mean_range']})."]
    if "chain" in o:
        ch = o["chain"]
        L += ["", f"**Mode-W chain at {ch['vth']} V** (P3.3, {ch['n']} steps, 1 s VDD-on idle between): {ch['correct']} / {ch['valid']} "
              f"({ftxt(ch['failures'])}); same outcome as the independent runs {ch['same_outcome']}/{ch['n']}; race shift {ch['race_shift_us']} µs; "
              f"changed: {ch['changed']}."]
    (S / "e1_tables.md").write_text("\n".join(L) + "\n")


def e2_tables(o):
    base = {k.split("_", 2)[2]: v for k, v in o["rates"]["1"]["outcomes"].items()}
    L = ["**E2: ramp-rate stress (5 runs per rate, 134 TFTs, nominal die, mode G).** Stress = max(|V_GS|, |V_GD|), limit 3.5 V.", "",
         "| Rate (× C2) | Ramp (µs) / slope (V/µs) | Segment | TFTs > 3.5 V | Worst TFT: max \\|V_GS\\| / \\|V_GD\\| (V), at (µs) | Margin (V) | Crossbar peak (V) | Most negative internal node (V) | Outcomes vs 1× |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r, x in sorted(o["rates"].items(), key=lambda kv: float(kv[0])):
        oc = {k.split("_", 2)[2]: v for k, v in x["outcomes"].items()}
        same = sum(oc[k]["read"] == base[k]["read"] for k in base)
        sh = max(abs(oc[k]["race_us"] - base[k]["race_us"]) for k in base)
        for s, lab in (("up", "power-up + classification"), ("down", "power-down + 1 s off")):
            y = x[s]; w = y["worst"]; c = y["crossbar"]; lo = y["lowest"]
            L.append(f"| {float(r):g}× | {x['ramp_us']:.3g} / {x['slope_V_per_us']:.3g} | {lab} | {y['n_above']} | {w['device']}: {w['max_vgs']:.3f} / {w['max_vgd']:.3f}, "
                     f"{w['t_max_us']:.2f} | {3.5 - w['max_stress']:.3f} | {c['max_stress']:.3f} ({c['device']}, {c['t_max_us']:.2f} µs) | "
                     f"{lo['V']:.3f} ({lo['node']}, {lo['t_us']:.2f} µs) | " + (f"{same}/5 same, race shift ≤ {sh:.2f} µs" if s == "up" else "") + " |")
    (S / "e2_tables.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    w = sys.argv[1]
    if w in ("E1", "all"):
        o = e1()
        print((S / "e1_tables.md").read_text())
    if w in ("E2", "all"):
        import stress_ramp
        e2_tables(stress_ramp.summarize())
        print((S / "e2_tables.md").read_text())
