"""Study 1 summary (DECISIONS S1.4-S1.5), recomputed from per-run JSONs. -> summary/s1_modew.json, summary/s1_tables.md
Reused cells (S1.3) take their 20 outcomes from the reference runs (host_v21 E1 / host_v2 C3) after the netlist-identity
check (summary/s1_identity.json) and the 2 re-simulated samples (raw/S1) agree."""
import json, math
import numpy as np
import wu
import s1_modew as S


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(c - h, 0.0), 6), round(min(c + h, 1.0), 6)]


def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    return round(min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n), 6)


def correct(m):
    return bool(m.get("valid_read")) and m.get("winner_read") == m.get("label")


def outcome(m):
    return (tuple(m.get("latched_read") or []), bool(m.get("valid_read")), m.get("failure_read"))


def block(runs):
    n = len(runs)
    c = sum(correct(m) for m in runs)
    v = sum(bool(m.get("valid_read")) for m in runs)
    fails = {}
    for m in runs:
        f = m.get("failure_read") if "failure_read" in m else "no_data"
        if f:
            fails[f] = fails.get(f, 0) + 1
    races = [m["race_us"] for m in runs if m.get("race_us") is not None]
    E = [m["energy_nJ"]["total"] for m in runs if "energy_nJ" in m]
    return dict(n=n, correct=c, accuracy_wilson95=wilson(c, n), valid=v, failures=fails,
                race_us_median=round(float(np.median(races)), 1) if races else None,
                energy_nJ_median=round(float(np.median(E)), 1) if E else None,
                reading="works" if c >= 13 else ("fails" if c == 0 else "degraded"))


def cal_info(c):
    if c.get("failed"):
        return dict(failed=True)
    return dict(mode=c["mode"], vhat=round(c["vhat"], 5), err_mV=round(c["err_mV"]["a1"], 2), mu_hat=round(c["mu_hat"], 4),
                mu_err_pct=round(100 * c["mu_err_rel"], 2), k=round(c["k"], 4), levels=list(c["levels"]), flag=c["flag"],
                race_t_us=c["race"]["t_us"])


def idle_uW(tag):
    f = wu.RAW / "S1idle" / f"{tag}_idle.json"
    return json.load(open(f)).get("P_mean_uW") if f.exists() else None


def v2_cell(vth, muf):
    k = f"v{round(vth*1000):04d}_m{round(muf*100):03d}"
    runs = [json.load(open(wu.HV2RAW / "C3" / f"C3_{k}_learned_s{i:02d}.json")) for i in wu.SUB]
    return block(runs)


def main():
    ident = json.load(open(wu.SUMM / "s1_identity.json")) if (wu.SUMM / "s1_identity.json").exists() else {}
    out = dict(aging={}, mismatch={}, notes=[])
    for v, m in S.AGING:
        c = wu.calibrate(key=wu.ckey("S1", v, m), vth=v, muf=m)
        rec = dict(vth=v, muf=m, delta_vth=round(v - 0.55, 2), cal=cal_info(c))
        if c.get("failed"):
            rec["result"] = "calibration failed"
            out["aging"][c["key"]] = rec
            continue
        if S.reused(c):
            f, rdir, pat = S.ref_cal(v, m)
            runs = [json.load(open(rdir / (pat.format(i) + ".json"))) for i in wu.SUB]
            checks = []
            for i in S.RESIM:
                a = json.load(open(wu.RAW / "S1" / f"S1_{c['key']}_v21_s{i:02d}.json"))
                b = json.load(open(rdir / (pat.format(i) + ".json")))
                dt = max([abs(a[x] - b[x]) for x in ("race_us", "t_read_us") if a.get(x) is not None and b.get(x) is not None] or [0.0])
                checks.append(dict(idx=i, same_outcome=outcome(a) == outcome(b), max_time_diff_us=round(dt, 4)))
            rec.update(source=f"reused: {rdir.relative_to(wu.REPO)} ({pat.format(0)[:-2]}*)", identity=ident.get(c["key"]),
                       resim=checks, resim_ok=all(x["same_outcome"] and x["max_time_diff_us"] <= 0.05 for x in checks))
        else:
            runs = [json.load(open(wu.RAW / "S1" / f"S1_{c['key']}_v21_s{i:02d}.json")) for i in wu.SUB]
            rec["source"] = "results/wrapup/raw/S1"
        rec.update(block(runs))
        rec["modes_of_runs"] = sorted({r.get("mode", "G") for r in runs})
        if c["mode"] == "W":
            P = [idle_uW(r["tag"]) for r in runs]
            P = [p for p in P if p is not None]
            rec["standby_uW_median"] = round(float(np.median(P)), 1) if P else None
            if rec["source"].startswith("reused") and (v, m) == (0.55, 1.0):      # idles of the reused E1 runs
                e1 = json.load(open(wu.HV21RAW.parent / "summary/e1_lower_edge.json"))["points"]["0.55"]
                rec["standby_uW_median"] = round(float(e1["standby_uW_mean_med"]), 1)
                rec["standby_source"] = "host_v21 summary/e1_lower_edge.json (E1idle)"
        rec["v2_reference"] = dict(cell=f"C3 {round(v + 0.10, 2):.2f} V x{m}", **v2_cell(round(v + 0.10, 2), m))
        out["aging"][c["key"]] = rec
    # mismatch
    pairs = []
    allruns = []
    for d in S.DIES:
        c = wu.calibrate(key=wu.ckey("S1", 0.55, 1.0, die=d), vth=0.55, muf=1.0, mc=d["mc"])
        runs = [json.load(open(wu.RAW / "S1" / f"S1_{c['key']}_v21_s{i:02d}.json")) for i in wu.SUB]
        ref = [json.load(open(wu.HV2RAW / "C4" / f"C4_v0650_m100_an20d{d['die']:02d}_learned_s{i:02d}.json")) for i in wu.SUB]
        allruns += runs
        pairs += list(zip([correct(r) for r in runs], [correct(r) for r in ref]))
        out["mismatch"][f"die{d['die']}"] = dict(cal=cal_info(c), **block(runs), c4=block(ref))
    b = sum(x and not y for x, y in pairs); cc = sum(y and not x for x, y in pairs)
    c4all = [json.load(open(wu.HV2RAW / "C4" / f"C4_v0650_m100_an20d{d['die']:02d}_learned_s{i:02d}.json")) for d in S.DIES for i in wu.SUB]
    pooled = block(allruns)
    pooled["paired_vs_C4"] = dict(n=len(pairs), both=sum(x and y for x, y in pairs), only_S1=b, only_C4=cc,
                                  neither=sum(not x and not y for x, y in pairs), mcnemar_p=mcnemar(b, cc))
    pooled["C4"] = block(c4all)
    pooled["reading"] = "worse than v2" if (cc > b and pooled["paired_vs_C4"]["mcnemar_p"] < 0.05) else "matches v2"
    out["mismatch"]["pooled"] = pooled
    ok_cells = all(r.get("reading") == "works" for r in out["aging"].values())
    out["study1_success"] = bool(ok_cells and pooled["reading"] == "matches v2")
    json.dump(out, open(wu.SUMM / "s1_modew.json", "w"), indent=1, default=float)
    # tables
    L = ["| \\|V_th\\| (ΔV_th from 0.55 V) | µ | mode (V̂, error) | µ̂ (error), k | correct / valid of 20 (Wilson 95 %) | failures | race median (µs) | source | v2 reference (base 0.65 V + ΔV_th): correct / valid |",
         "|---|---|---|---|---|---|---|---|---|"]
    for k, r in out["aging"].items():
        cl = r["cal"]
        w = r["accuracy_wilson95"]
        L.append(f"| {r['vth']:.2f} V (+{r['delta_vth']:.2f}) | ×{r['muf']:g} | {cl['mode']} ({cl['vhat']:.4f} V, {cl['err_mV']:+.1f} mV) | "
                 f"{cl['mu_hat']:.3f} ({cl['mu_err_pct']:+.1f} %), {cl['k']:.3f} | **{r['correct']} / {r['valid']}** ({100*w[0]:.1f}–{100*w[1]:.1f} %) | "
                 f"{', '.join(f'{a} {b}' for a, b in r['failures'].items()) or '—'} | {r['race_us_median']} | "
                 f"{'reused (identical netlists)' if r['source'].startswith('reused') else 'simulated'} | "
                 f"{r['v2_reference']['cell']}: {r['v2_reference']['correct']} / {r['v2_reference']['valid']} |")
    L += ["", "| Die | mode (V̂) | correct / valid of 20 | C4 (v2, same die at 0.65 V) correct / valid |", "|---|---|---|---|"]
    for k, r in out["mismatch"].items():
        if k == "pooled":
            continue
        L.append(f"| {k} | {r['cal']['mode']} ({r['cal']['vhat']:.4f} V) | {r['correct']} / {r['valid']} | {r['c4']['correct']} / {r['c4']['valid']} |")
    p = out["mismatch"]["pooled"]
    L.append(f"| **pooled** | | **{p['correct']} / {p['valid']}** of 100 ({100*p['accuracy_wilson95'][0]:.1f}–{100*p['accuracy_wilson95'][1]:.1f} %) | "
             f"{p['C4']['correct']} / {p['C4']['valid']}; paired S1-only {p['paired_vs_C4']['only_S1']} / C4-only {p['paired_vs_C4']['only_C4']}, "
             f"McNemar p = {p['paired_vs_C4']['mcnemar_p']} |")
    (wu.SUMM / "s1_tables.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print("study1_success", out["study1_success"])


if __name__ == "__main__":
    main()
