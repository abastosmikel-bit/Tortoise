"""Markdown tables for REPORT.md, generated from the summary JSONs (so the report's numbers come from the data files).
Usage: python3 report_tables.py   -> summary/report_tables.md (sections that have data are written; others skipped)"""
import json
import numpy as np
import wcommon as W

S = W.SUMM


def j(name):
    p = S / name
    return json.loads(p.read_text()) if p.exists() else None


def hu(x, d=1):
    """Round half up once, from the decimal representation (audit finding 2: no double or banker's rounding)."""
    from decimal import Decimal, ROUND_HALF_UP
    return str(Decimal(str(x)).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP))


def pc(x, d=1):
    from decimal import Decimal
    return "—" if x is None else f"{hu(Decimal(str(x)) * 100, d)} %"


def ci(w):
    from decimal import Decimal
    return "—" if not w or w[0] is None else f"{hu(Decimal(str(w[0])) * 100)}–{hu(Decimal(str(w[1])) * 100)} %"


def ceilings():
    d = j("A0_ceilings.json")
    if not d:
        return ""
    names = [("lr_bias_free", "Float linear, per-class bias, free weights (multinomial LR)"),
             ("svm_cs", "Float linear, bias (Crammer–Singer SVM)"), ("svm_ovr", "Float linear, bias (one-vs-rest SVM)"),
             ("lda", "Float linear, bias (shrinkage LDA)"), ("lr_nobias_free", "Float, no bias, free column sums"),
             ("lr_bias_eqcol", "Float, bias, equal column sums"),
             ("lr_nobias_eqcol", "**Float, no bias, equal column sums = crossbar form** (non-negativity is free)"),
             ("int_round", "Integer fingers (Σ = 60, 15–21 banks): rounded crossbar-form LR"),
             ("int_ls", "Integer fingers: + local search on the training count"), ("int_milp", "Integer fingers: + MILP polish"),
             ("old_weights", "Old weights (trained on all 210: **in-sample**)")]
    out = ["| Classifier | CV accuracy, mean of 10 repeats (SD over repeats) | Range over repeats | Training accuracy |", "|---|---|---|---|"]
    for k, lab in names:
        v = d["summary"][k]
        out.append(f"| {lab} | {pc(v['cv_accuracy_mean'])} ({hu(100 * v['cv_accuracy_sd_over_repeats'])}) | "
                   f"{pc(v['cv_accuracy_min_repeat'])}–{pc(v['cv_accuracy_max_repeat'])} | {pc(v.get('train_accuracy_mean'))} |")
    return "### Ceilings (A0)\n\n" + "\n".join(out) + "\n"


def calibration():
    d = j("A0_calibration.json")
    if not d:
        return ""
    f, dg = d["fit"], d["diagnostics"]
    rows = [("C1 transfer α (V per finger·µs), c₀", f"{f['alpha']:.4e}, {1e3 * f['c0']:.1f} mV; rms residual {dg['c1_fit']['rms_residual_mV']:.2f} mV over {dg['c1_fit']['n_points']} rails"),
            ("Gap slope s_g (losers' gap vs rail deficit)", f"{dg['gap_slope']['slope_mV_per_us']:.3f} mV/µs ({dg['gap_slope']['n_points']} points, median relative residual {100 * dg['gap_slope']['rel_residual_median']:.1f} %)"),
            ("Average C2 slope s̄, gap factor s̄/s_g", f"{dg['race']['s_bar_mV_per_us']:.4f} mV/µs, {dg['race']['gap_factor']:.4f}"),
            ("Effective trip level Θ_k (V)", ", ".join(f"{x:.4f}" for x in f["Theta"]) + f"; trip-time residual {dg['race']['trip_time_rms_residual_us']:.2f} µs rms"),
            ("Rail reset level R_k (V)", ", ".join(f"{x:.4f}" for x in f["R"])),
            ("Resolve threshold G_res", f"{f['G_res']:.2f} µs (largest failed gap {dg['resolve']['largest_failed_gap_us']} µs, smallest valid {dg['resolve']['smallest_valid_gap_us']} µs; {dg['resolve']['n_invalid']}/{dg['resolve']['n']} invalid)"),
            ("Lock latency (valid runs)", f"median {d['lock_latency_us']['p50']:.2f} µs, range {d['lock_latency_us']['p0']:.2f}–{d['lock_latency_us']['p100']:.2f} µs (N = {d['lock_latency_us']['n']})"),
            ("Gap scale vs lab rev10 schemeA.py model", f"SPICE/model median {d['lab_model_gap_ratio_K']['median_ratio']:.3f} (r = {d['lab_model_gap_ratio_K']['pearson_r']:.4f}, N = {d['lab_model_gap_ratio_K']['n']})")]
    out = ["| Quantity (K, 40 runs, old weights) | Value |", "|---|---|"] + [f"| {a} | {b} |" for a, b in rows]
    ag = ["| Agreement with SPICE | N | Winner | Validity | Correct/incorrect | Gap r | Gap SPICE/surrogate (median) | Gap error median / max |", "|---|---|---|---|---|---|---|---|"]
    for key, lab in (("agreement_K_in_sample", "K, in-sample"), ("agreement_K_cv5", "K, 5-fold CV inside K"), ("agreement_S_heldout", "**S, held out (40)**")):
        v = d.get(key)
        if v:
            ag.append(f"| {lab} | {v['n']} | {v['first_agree']}/{v['n']} | {v['validity_agree']}/{v['n']} | {v['correct_agree']}/{v['n']} | "
                      f"{v.get('gap_pearson_r', float('nan')):.4f} | {v.get('gap_ratio_spice_over_sur_median', float('nan')):.3f} | "
                      f"{v.get('gap_abs_err_median_us', float('nan')):.1f} / {v.get('gap_abs_err_max_us', float('nan')):.1f} µs |" if 'gap_pearson_r' in v else
                      f"| {lab} | {v['n']} | {v['first_agree']}/{v['n']} | {v['validity_agree']}/{v['n']} | {v['correct_agree']}/{v['n']} | — | — | — |")
    mm = j("A0_mismatch.json")
    if mm:
        c = mm["chain_fit"]
        ch = ["| Device (class chain) | W·L (µm²) | Effect per volt of ΔV_th |", "|---|---|---|"]
        ch.append(f"| Reset switch {c['reset']['device']} (rail start level) | {c['reset']['area']:.0f} | {c['reset']['coef']:+.3f} (reset level {c['reset']['reset_level_coef']:+.3f}) |")
        for k, v in c["chain"].items():
            ch.append(f"| {k} {v['device']} (trip level) | {v['area']:.0f} | {v['coef']:+.4f} |")
        b = c["bank_check"]
        ch.append(f"| Crossbar bank {b['device']} ({b['fingers']} fingers), +{1000 * b['dvth']:.0f} mV | — | trip shift SPICE {b['spice_dt_us']:.1f} µs vs surrogate {b['surrogate_dt_us']:.1f} µs |")
        m = mm.get("mm_check")
        mmt = (f"\nMismatch check (3 dies × 10 K samples, anchor 35 mV, surrogate fed the same draws): winner {m['first_agree']}/{m['n']}, "
               f"validity {m['validity_agree']}/{m['n']}, correct/incorrect {m['correct_agree']}/{m['n']}; the die changed the SPICE winner in "
               f"{m['n_winner_changed_by_die_spice']} runs and the surrogate predicted all {m['n_winner_changed_by_die_surrogate_agrees']}.\n") if m else ""
    else:
        ch, mmt = [], ""
    rt = j("A0_retrim.json")
    rtt = []
    if rt:
        rtt = ["| Re-trimmed \\|V_th\\| | Runs | ref − reset (V) | Θ shift (mV) | Trips in C1 (SPICE / surrogate) | Winner / validity / outcome agreement |", "|---|---|---|---|---|---|"]
        for k, v in rt.items():
            a = v["agreement_in_sample"]; c1 = v["C1_trip_pred_vs_spice"]
            rtt.append(f"| {k} V | {v['n']} | {v['window_ref_minus_reset_V']:.3f} | {1e3 * v['theta_shift_V']:+.1f} | {c1['both'] + c1['spice_only']} / {c1['both'] + c1['sur_only']} | "
                       f"{a['first_agree']}/{a['n']}, {a['validity_agree']}/{a['n']}, {a['correct_agree']}/{a['n']} |")
    cs = j("A0_colsum_check.json")
    cst = (f"\nUnequal column sums (W13 check, `probe_le60`, sums {cs['colsums']}, 20 K runs): winner {cs['agreement']['first_agree']}/20, validity "
           f"{cs['agreement']['validity_agree']}/20, correct/incorrect {cs['agreement']['correct_agree']}/20; C2 slope ratio of the 58-finger columns "
           f"{cs['slope_ratio_58_over_60']:.3f} (expected 58/60 = {cs['expected_ratio']:.3f}).\n") if cs else ""
    return ("### Surrogate calibration (A0)\n\n" + "\n".join(out) + "\n\n" + "\n".join(ag) + "\n\n" + "\n".join(ch) + "\n" + mmt + "\n" +
            "\n".join(rtt) + "\n" + cst)


def a1_cv():
    d = j("A1_cv.json")
    if not d:
        return ""
    out = ["| Family | Column sums | Config | **S ×100** (SD over 4 repeats) | A_nom | A_mm (20 / 35 mV) | A_rt | A_rt at 0.95 V | Banks (median) | Smallest column sum (median) |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    best = {f: b["key"] for f, b in d.get("best_per_family", {}).items()}
    lab = {"a": "(a) margin", "b": "(b) mismatch", "c": "(c) re-trim"}
    for fam, cfgs in d["families"].items():
        for key, v in cfgs.items():
            mark = " ◀ best" if best.get(fam) == key else ""
            cfg = (f"m = {v['config']} µs" if fam == "a" else
                   (f"τ = {v['config'].split('m')[0]}, m = {v['config'].split('m')[1]} µs" if "m" in str(v["config"]) else f"τ = {v['config']} µs"))
            out.append(f"| {lab[fam]} | {'= 60' if v['mode'] == 'eq60' else '50–60'} | {cfg}{mark} | **{hu(100 * v['S'])}** ({hu(100 * v['S_sd_repeats'])}) | "
                       f"{pc(v['A_nom'])} | {pc(v['A_mm'])} ({pc(v['A_mm20'])} / {pc(v['A_mm35'])}) | {pc(v['A_rt'])} | {pc(v['rt_by_vth']['0.95'])} | "
                       f"{v['banks_median']:.1f} | {v['colsum_min_median']:.1f} |")
    for n, v in d.get("references", {}).items():
        out.append(f"| reference: {n.replace('_', ' ')} | — | — | {100 * v['S']:.1f} | {pc(v['A_nom'])} | {pc(v['A_mm'])} ({pc(v['A_mm20'])} / {pc(v['A_mm35'])}) | "
                   f"{pc(v['A_rt'])} | {pc(v['rt_by_vth']['0.95'])} | — | — |")
    return "### A1 CV on T (surrogate; 20 group splits)\n\n" + "\n".join(out) + "\n"


def a1_select():
    d = j("A1_select.json")
    if not d:
        return ""
    out = ["| Weights | Banks / TFTs | Column sums | CV score S | **SPICE on S: correct** (Wilson 95 %) | Valid | Surrogate agreement (winner / outcome) | vs old on S (both / old only / new only / neither) |",
           "|---|---|---|---|---|---|---|---|"]
    for n, r in d["results"].items():
        F = np.array(r["F"]) if "F" in r else W.F_OLD
        vs = r.get("vs_old_on_S")
        out.append(f"| {n}{' ◀ winner' if n == d['winner'] else ''} | {int((F > 0).sum())} / {W.n_tft(F)} | {F.sum(0).tolist()} | "
                   f"{100 * r['cv']['S']:.1f} |" if r.get("cv") else f"| {n} | {int((F > 0).sum())} / {W.n_tft(F)} | {F.sum(0).tolist()} | — |")
        out[-1] += (f" **{r['correct']}/{r['n']}** ({ci(r['wilson95'])}) | {r['valid']}/{r['n']} | {r['surrogate_agreement']['first_agree']}/{r['n']} / "
                    f"{r['surrogate_agreement']['correct_agree']}/{r['n']} | " + (f"{vs['both']} / {vs['old_only']} / {vs['new_only']} / {vs['neither']} |" if vs else "— |"))
    return "### A1 SPICE selection on S\n\n" + "\n".join(out) + "\n"


def a2(name="FINAL_frozen"):
    d = j(f"A2_{name}.json")
    if not d:
        return ""
    a, o, p = d["accuracy"], d["old_weights"], d["paired"]
    f1 = lambda x: "—" if x is None else f"{x:.1f}"
    fails = lambda f: ", ".join(f"{k} ×{v}" for k, v in f.items()) or "none"
    g, og = d["gap_reach_us"], o["gap_reach_us"]
    out = ["| Measure | New weights (FINAL_frozen = cand_a) | Old weights (campaign Phase 1, Variant 3) |", "|---|---|---|",
           f"| SPICE accuracy (invalid = wrong) | **{a['correct']}/{a['n']} = {pc(a['value'])}** ({ci(a['wilson95'])}) | {o['correct']}/{o['n']} = {pc(o['value'])} ({ci(o['wilson95'])}) |",
           f"| Validity | {d['validity']['valid']}/{d['validity']['n']} = {pc(d['validity']['value'])} ({ci(d['validity']['wilson95'])}) | {o['validity']['valid']}/{o['validity']['n']} = {pc(o['validity']['value'])} ({ci(o['validity']['wilson95'])}) |",
           f"| Failures | {fails(d['failures'])} | {fails(o['failures'])} |",
           f"| Software argmax accuracy (same weights) | {pc(d['software_argmax_accuracy'])} | {pc(o['software_argmax_accuracy'])} |",
           f"| Surrogate: accuracy / winner agreement / outcome agreement | {pc(d['surrogate']['accuracy'])} / {d['surrogate']['first_agree']}/90 / {d['surrogate']['correct_agree']}/90 | — |",
           f"| Surrogate vs SPICE gap (same winner and runner-up) | r = {d['surrogate']['gap_pearson_r']:.4f}, SPICE/surrogate median {d['surrogate']['gap_ratio_spice_over_sur_median']:.3f} (N = {d['surrogate']['gap_pairs']}) | — |",
           f"| Runner-up gap, valid runs: median / 5th pct / min | {f1(g.get('p50'))} / {f1(g.get('p5'))} / {f1(g.get('p0'))} µs | {f1(og.get('p50'))} / {f1(og.get('p5'))} / {f1(og.get('p0'))} µs |",
           f"| Valid runs with gap < 20 µs | {d['n_gap_below_20us']} | {o['n_gap_below_20us']} |",
           f"| Lock latency, valid runs: median (range) | {f1(d['lock_latency_us'].get('p50'))} µs ({f1(d['lock_latency_us'].get('p0'))}–{f1(d['lock_latency_us'].get('p100'))}) | {f1(o['lock_latency_us'].get('p50'))} µs ({f1(o['lock_latency_us'].get('p0'))}–{f1(o['lock_latency_us'].get('p100'))}) |",
           f"| Race from C2: median (range) | {d['race_from_C2_us'].get('p50'):.0f} µs ({d['race_from_C2_us'].get('p0'):.0f}–{d['race_from_C2_us'].get('p100'):.0f}) | {o['race_from_C2_us'].get('p50'):.0f} µs ({o['race_from_C2_us'].get('p0'):.0f}–{o['race_from_C2_us'].get('p100'):.0f}) |",
           f"| Trips during C1 | {d['n_trip_in_C1']} | {o['n_trip_in_C1']} |",
           f"| TFTs / non-empty banks | {d['n_tft']} / {d['banks']} | {o['n_tft']} / 21 |"]
    pt = (f"\n**Paired with the old weights (same 90 samples):** both correct {p['both_correct']}, old only {p['old_only']}, new only {p['new_only']}, "
          f"both wrong {p['both_wrong']}; difference {100 * p['difference']:+.1f} points; exact two-sided McNemar p = {hu(p['mcnemar_exact_two_sided_p'], 3)}.\n")
    cmt = lambda cm: ["| label \\ SPICE | 1 | 2 | 3 | 4 | 5 | invalid |", "|---|---|---|---|---|---|---|"] + [f"| {i + 1} | " + " | ".join(str(x) for x in r) + " |" for i, r in enumerate(cm)]
    c = d["chain"]
    ch = (f"\n**Chain (test 30–39 in sequence, from this weight set's warm start):** same outcome as the independent runs {c['n_same_outcome']}/{c['n']}; correct {c['correct']}/10; "
          f"largest first-trip shift {max(abs(r['d_first_trip_us']) for r in c['rows'] if r['d_first_trip_us'] is not None):.2f} µs; largest gap shift "
          f"{max(abs(r['d_gap_us']) for r in c['rows'] if r['d_gap_us'] is not None):.2f} µs; largest rail reset-level change {max(r['d_reset_level_mV_max'] for r in c['rows']):.2f} mV.\n")
    return ("### A2 test set (90 samples, run once)\n\n" + "\n".join(out) + "\n" + pt + "\nConfusion matrix, new weights:\n\n" + "\n".join(cmt(d["confusion"]["matrix"]))
            + "\n\nConfusion matrix, old weights (campaign):\n\n" + "\n".join(cmt(o["confusion"])) + "\n" + ch)


def a3(name="FINAL_frozen"):
    d = j(f"A3_{name}.json")
    if not d:
        return ""
    fails = lambda f: ", ".join(f"{k} ×{v}" for k, v in f.items()) or "—"
    rm = lambda x: "—" if x is None else f"{x:.0f}"

    def row(lab, v, extra=""):
        n, o, p = v["new"], v["old"], v["paired"]
        return (f"| {lab} | **{n['correct']}/{n['n']}** ({ci(n['wilson95'])}) | {n['valid']}/{n['n']} | {fails(n['failures'])} | "
                f"{o['correct']}/{o['n']} | {o['valid']}/{o['n']} | {fails(o['failures'])} | {p['new_only']} / {p['old_only']} (p = {hu(p['mcnemar_exact_p'], 3)}) | {rm(n['race_from_C2_median_us'])} / {rm(o['race_from_C2_median_us'])} µs |{extra}")
    hdr = ["| Point | New: correct (Wilson 95 %) | New: valid | New: failures | Old: correct | Old: valid | Old: failures | Paired: new only / old only (exact McNemar p) | Race median new / old |",
           "|---|---|---|---|---|---|---|---|---|"]
    A = hdr + [row("nominal (0.65 V, µ ×1; A2 / campaign Phase 1 runs)", d["nominal"])]
    lab = {"vth045": "\\|V_th\\| 0.45 V", "vth055": "\\|V_th\\| 0.55 V", "vth075": "\\|V_th\\| 0.75 V", "vth085": "\\|V_th\\| 0.85 V",
           "vth095": "\\|V_th\\| 0.95 V", "vth105": "\\|V_th\\| 1.05 V", "mu050": "µ ×0.5", "mu075": "µ ×0.75", "mu125": "µ ×1.25"}
    for k, v in d["3A_fixed_levels"].items():
        A.append(row(lab[k], v))
    T = [hdr[0] + " Strict (no trip in C1) new / old | Trips in C1 new / old |", hdr[1] + "---|---|"]
    for k, v in d["3A_T_retrimmed"].items():
        T.append(row(lab[k] + f" (V₁ {v['levels']['V1']} / V₂ {v['levels']['V2']} V)", v,
                     f" {v['new']['strict_correct']}/20 / {v['old']['strict_correct']}/20 | {v['new']['n_trip_in_C1']} / {v['old']['n_trip_in_C1']} |"))
    V = [hdr[0] + " Median die new / old |", hdr[1] + "---|"]
    for k, v in d["3B_V"].items():
        V.append(row(k.replace("anchor_", "anchor ").replace("mV", " mV"), v, f" {100 * v['new_die_median']:.0f} % / {100 * v['old_die_median']:.0f} % |"))
    return ("### A3 robustness (20-sample subset)\n\nFixed host levels (drift budget):\n\n" + "\n".join(A) + "\n\nRe-trimmed host levels (process window):\n\n" + "\n".join(T)
            + "\n\nSize-scaled V_th mismatch (3B-V), 5 dies × 20 samples per anchor, same seeds as the campaign:\n\n" + "\n".join(V) + "\n")


def stress(name="FINAL_frozen"):
    d = j(f"A3_stress_{name}.json")
    if not d:
        return ""
    o = d["old_weights"]
    sel = ", ".join(f"{k} #{v}" for k, v in d["selection"].items())
    out = [f"Runs: {sel}, chain #31. Devices audited: {d['n_devices']} (crossbar {d['crossbar']['n']}). **Above 3.5 V: {d['n_over_limit']}** (old weights: {o['n_over_limit']} of {o['n_devices']}).",
           "", "| Rank | Device | Max \\|V_G·\\| (V) | Margin (V) | When (µs) | Run |", "|---|---|---|---|---|---|"]
    for i, w in enumerate(d["worst10"], 1):
        out.append(f"| {i} | {w['device']} | {w['max_stress']:.3f} | {w['margin_V']:.3f} | {w['t_max_us']} | {w['run']} |")
    out.append(f"\nCrossbar maximum: new {d['crossbar']['max_stress']:.3f} V ({d['crossbar']['worst'][0]['device']}) vs old {o['crossbar_max']:.3f} V; worst device overall old: {o['worst']['device']} {o['worst']['max_stress']:.3f} V.")
    return "### A3 stress audit\n\n" + "\n".join(out) + "\n"


def no_old():
    d = j("A4_no_old_start.json")
    if not d:
        return ""
    out = ["| Configuration | CV score S ×100, as run (with the old-weights start) | S ×100 without it | A_nom / A_mm / A_rt without it | Splits whose weights changed |",
           "|---|---|---|---|---|"]
    for k, v in d.items():
        r, n = v["reported"], v["without_old_start"]
        out.append(f"| {k.replace('_', ' ')} | {hu(100 * r['S'])} ({hu(100 * r['S_sd_repeats'])}) | **{hu(100 * n['S'])}** ({hu(100 * n['S_sd_repeats'])}) | "
                   f"{pc(n['A_nom'])} / {pc(n['A_mm'])} / {pc(n['A_rt'])} | {v['splits_with_different_weights']}/20 |")
    return "### A4 sensitivity: CV without the old-weights start\n\n" + "\n".join(out) + "\n"


SECTIONS = dict(CEILINGS=ceilings, CALIBRATION=calibration, A1_CV=a1_cv, A1_SELECT=a1_select, A2=a2, A3=a3, STRESS=stress, NO_OLD=no_old)


def assemble(template, out):
    """Replace every {{TABLE:<name>}} marker in the template with the generated section (without its ### heading)."""
    import re
    txt = template.read_text()

    def rep(m):
        sec = SECTIONS[m.group(1)]()
        return "\n".join(l for l in sec.splitlines() if not l.startswith("### ")).strip() if sec else f"*({m.group(1)}: not available yet)*"
    out.write_text(re.sub(r"\{\{TABLE:(\w+)\}\}", rep, txt))


if __name__ == "__main__":
    txt = "# Report tables (generated by scripts/report_tables.py from summary/*.json)\n\n" + "\n".join(f() for f in SECTIONS.values())
    (S / "report_tables.md").write_text(txt)
    tpl = W.WS / "scripts/REPORT_template.md"
    if tpl.exists():
        assemble(tpl, W.WS / "REPORT.md")
        print("REPORT.md assembled")
    print(txt[:200])
