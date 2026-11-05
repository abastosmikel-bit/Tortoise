"""Recompute every summary number from the raw per-run JSONs (raw/<phase>/*.json) and summary/analytic.csv.
Usage: python3 summarize.py [phase1|chain|phase3A|phase3B|phase3A_T|phase3B_P|phase3B_V|all]   -> summary/*.json, summary/*.csv"""
import csv, glob, json, math, sys
import numpy as np
import common as C

S = C.SUMM


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(round(c - h, 4), 0.0) + 0.0, min(round(c + h, 4), 1.0))


def load(phase):
    out = []
    for f in sorted(glob.glob(str(C.RAW / f"{phase}/*.json"))):
        if f.endswith("_draws.json"):
            continue
        out.append(json.load(open(f)))
    return out


def analytic():
    return {int(r["idx"]): r for r in csv.DictReader(open(C.CAMP / "summary/analytic.csv"))}


def outcome(m):
    """SPICE predicted class for scoring: the latched class if valid, else None (counted wrong)."""
    return m["winner"] if m.get("valid") else None


def pct(x, qs=(0, 5, 25, 50, 75, 95, 100)):
    x = np.asarray([v for v in x if v is not None], float)
    return {f"p{q}": round(float(np.percentile(x, q)), 3) for q in qs} if len(x) else {}


def failure(m):
    """Failure type from the raw fields. 'stuck_latched': one or more na high at the end without any trip edge after
    320 us (the latches never reset low); 'timeout': no trip and nothing latched; 'lockout_failed': see below."""
    if m.get("valid"):
        return None
    f = m.get("failure") or "no_data"
    if f == "timeout" and m.get("latched"):
        return "stuck_latched"
    # 'lockout_failed': several latched and at least one latched class tripped AFTER the lock engaged
    # (as opposed to a near tie where all latched classes tripped before the lock)
    if f == "multi_latched" and m.get("lock_us") and any(
            m["trip_us"].get(str(k), m["trip_us"].get(k, 0)) > m["lock_us"] for k in m["latched"]):
        return "lockout_failed"
    return f


def acc_block(runs):
    n = len(runs); k = sum(1 for m in runs if outcome(m) == m["label"]); nv = sum(1 for m in runs if m.get("valid"))
    fails = {}
    for m in runs:
        if not m.get("valid"):
            fails[failure(m)] = fails.get(failure(m), 0) + 1
    return dict(n=n, correct=k, accuracy=round(k / n, 4) if n else None, accuracy_wilson95=wilson(k, n),
                valid=nv, validity=round(nv / n, 4) if n else None, validity_wilson95=wilson(nv, n), failures=fails)


def phase1():
    runs = load("phase1"); A = analytic()
    assert len(runs) == 90, len(runs)
    rows = []
    for m in sorted(runs, key=lambda m: m["idx"]):
        a = A[m["idx"]]; g = m.get("gap") or {}
        rows.append(dict(idx=m["idx"], label=m["label"], spice_class=outcome(m) or "", valid=m["valid"], failure=m.get("failure") or "",
                         first=m.get("first") or "", latched=";".join(map(str, m.get("latched") or [])),
                         trips=";".join(f"{k}:{v}" for k, v in sorted((m.get("trip_us") or {}).items())),
                         runner_up=m.get("runner_up") or "", gap_reach_us=g.get("gap_reach_us"), gap_slope_us=g.get("gap_slope_us"),
                         gap_dV_mV=g.get("dV_mV"), lock_latency_us=m.get("lock_latency_us"), lockb_chain_us=m.get("lockb_chain_us"),
                         trip_in_C1=m.get("trip_in_C1"), sw_winner=int(a["sw_winner"]), sA_winner=int(a["sA_winner"]),
                         sA_gap_us=float(a["sA_gap_us"]), sw_score_margin=round(float(a["sw_score_1"]) - float(a["sw_score_2"]), 3),
                         ref_reset=m.get("ref_reset"), wall_s=m["run"]["wall_s"]))
    with open(S / "phase1_runs.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    res = acc_block(runs)
    cm = np.zeros((5, 6), int)          # rows: label 1..5; cols: SPICE class 1..5, invalid
    for r in rows:
        cm[r["label"] - 1, (r["spice_class"] - 1) if r["spice_class"] else 5] += 1
    res["confusion"] = dict(rows="label 1..5", cols="SPICE class 1..5, invalid", matrix=cm.tolist())
    dis = [dict(idx=r["idx"], label=r["label"], spice=r["spice_class"] or f"invalid({r['failure']})", schemeA=r["sA_winner"],
                sA_gap_us=r["sA_gap_us"]) for r in rows if r["spice_class"] != r["sA_winner"]]
    res["spice_vs_schemeA"] = dict(agree=len(rows) - len(dis), n=len(rows), agreement=round((len(rows) - len(dis)) / len(rows), 4),
                                   disagreements=dis)
    res["schemeA_accuracy_same_samples"] = round(np.mean([r["sA_winner"] == r["label"] for r in rows]), 4)
    res["software_accuracy_same_samples"] = round(np.mean([r["sw_winner"] == r["label"] for r in rows]), 4)
    v = [r for r in rows if r["valid"]]
    gaps = [r["gap_reach_us"] if r["gap_reach_us"] is not None else r["gap_slope_us"] for r in v]
    lat = [r["lock_latency_us"] for r in v]
    marg = [g - l for g, l in zip(gaps, lat) if g is not None and l is not None]
    res["gap_vs_lock"] = dict(n_valid=len(v), runner_up_gap_us=pct(gaps), runner_up_gap_mV=pct([r["gap_dV_mV"] for r in v]), lock_latency_us=pct(lat), margin_gap_minus_latency_us=pct(marg),
                              n_gap_below_latency=sum(1 for x in marg if x < 0),
                              gap_below_latency=[dict(idx=r["idx"], gap_us=g, lat_us=r["lock_latency_us"], label=r["label"], spice=r["spice_class"])
                                                 for r, g in zip(v, gaps) if g is not None and r["lock_latency_us"] is not None and g < r["lock_latency_us"]],
                              n_second_class_tripped_but_not_latched=sum(1 for r in v if len(r["trips"].split(";")) > 1),
                              gap_definition="time for the runner-up rail to reach the level the first tripper's rail had at its trip (fallback: slope extrapolation)")
    # model vs SPICE runner-up gap (valid runs where both name the same runner-up)
    pr = [(float(A[r["idx"]]["sA_gap_us"]), r["gap_reach_us"]) for r in v
          if r["gap_reach_us"] is not None and int(A[r["idx"]]["sA_runner_up"]) == r["runner_up"]]
    if pr:
        a, b = np.array(pr).T
        res["gap_model_vs_spice"] = dict(n=len(pr), pearson_r=round(float(np.corrcoef(a, b)[0, 1]), 4),
                                         median_ratio_spice_over_model=round(float(np.median(b / a)), 4),
                                         note="schemeA is lab-calibrated; only the ratio/ordering is meaningful")
    race = [min(m["trip_us"].values()) - m["tC2_us"] for m in runs if m.get("trip_us")]
    res["race_time_from_C2_us"] = pct(race)
    res["n_trip_in_C1"] = sum(1 for m in runs if m.get("trip_in_C1"))
    res["wall_s"] = pct([m["run"]["wall_s"] for m in runs])
    (S / "phase1.json").write_text(json.dumps(res, indent=1, default=float))
    return res


def chain():
    ch = {m["idx"]: m for m in load("chain")}; ind = {m["idx"]: m for m in load("phase1")}
    rows = []
    for i in sorted(ch):
        c, d = ch[i], ind.get(i)
        if d is None:
            continue
        ft = lambda m: min(m["trip_us"].values()) if m.get("trip_us") else None
        rows.append(dict(idx=i, label=c["label"], chain_class=outcome(c), indep_class=outcome(d), chain_valid=c["valid"], indep_valid=d["valid"],
                         same_outcome=outcome(c) == outcome(d) and c["valid"] == d["valid"],
                         d_first_trip_us=round(ft(c) - ft(d), 3) if ft(c) and ft(d) else None,
                         d_lock_latency_us=round(c["lock_latency_us"] - d["lock_latency_us"], 3) if c.get("lock_latency_us") and d.get("lock_latency_us") else None,
                         d_reset_level_mV_max=round(max(abs(c["reset_level"][k] - d["reset_level"][k]) for k in c["reset_level"]) * 1e3, 3),
                         d_ref_reset_mV=round((c["ref_reset"] - d["ref_reset"]) * 1e3, 3),
                         d_runner_up_gap_us=round(c["gap"]["gap_reach_us"] - d["gap"]["gap_reach_us"], 3)
                         if c.get("gap") and d.get("gap") and c["gap"].get("gap_reach_us") is not None and d["gap"].get("gap_reach_us") is not None else None,
                         prev_winner_chain=ch[i - 1]["winner"] if i - 1 in ch else "warm start (class 5)"))
    res = dict(n=len(rows), n_same_outcome=sum(r["same_outcome"] for r in rows), rows=rows,
               chain_acc=acc_block([ch[i] for i in sorted(ch)]))
    (S / "chain.json").write_text(json.dumps(res, indent=1, default=float))
    return res


def phase3A():
    import phase3 as P
    sub = set(P.SUB); runs = load("phase3A"); p1 = {m["idx"]: m for m in load("phase1") if m["idx"] in sub}
    pts = {"vth065_mu100 (nominal, = Phase 1 runs)": list(p1.values())}
    for p, _ in P.A_POINTS:
        pts[p] = [m for m in runs if m["tag"].startswith(f"A_{p}_")]
    res = {}
    for p, rs in pts.items():
        b = acc_block(rs)
        b["race_time_from_C2_us"] = pct([min(m["trip_us"].values()) - m["tC2_us"] for m in rs if m.get("trip_us")], (0, 50, 100))
        b["lock_latency_us"] = pct([m.get("lock_latency_us") for m in rs if m.get("valid")], (0, 50, 100))
        b["n_trip_in_C1"] = sum(1 for m in rs if m.get("trip_in_C1"))
        b["n_spice_eq_phase1_nominal"] = sum(1 for m in rs if m["idx"] in p1 and outcome(m) == outcome(p1[m["idx"]]))
        res[p] = b
    (S / "phase3A.json").write_text(json.dumps(res, indent=1, default=float))
    return res


def phase3A_T():
    """Re-trimmed corner sweep, with the fixed-level result of the same point alongside."""
    import phase3 as P
    runs = load("phase3A_T"); fixed = json.load(open(S / "phase3A.json")); res = {}
    for p, vt in P.T_POINTS:
        rs = [m for m in runs if m["tag"].startswith(f"AT_{p}_")]
        b = acc_block(rs)
        b["levels"] = dict(V1=round(3.3 - vt - 0.83, 3), V2=round(3.3 - vt - 0.25, 3))
        b["race_time_from_C2_us"] = pct([min(m["trip_us"].values()) - m["tC2_us"] for m in rs if m.get("trip_us")], (0, 50, 100))
        b["lock_latency_us"] = pct([m.get("lock_latency_us") for m in rs if m.get("valid")], (0, 50, 100))
        b["n_trip_in_C1"] = sum(1 for m in rs if m.get("trip_in_C1"))
        # strict: a race that trips during integration (before C2) counts as a failure, even if one class latched
        ks = sum(1 for m in rs if outcome(m) == m["label"] and not m.get("trip_in_C1"))
        b["strict_correct_C2_resolved"] = ks
        b["strict_accuracy"] = round(ks / len(rs), 4) if rs else None
        b["strict_accuracy_wilson95"] = wilson(ks, len(rs))
        b["ref_minus_reset_V"] = round(float(np.median([m["ref_reset"] - np.mean(list(m["reset_level"].values())) for m in rs])), 4) if rs else None
        f = fixed.get(p, {})
        b["fixed_levels"] = dict(accuracy=f.get("accuracy"), validity=f.get("validity"), failures=f.get("failures"))
        res[p] = b
    p1 = load("phase1")
    res["nominal_vth065_ref_minus_reset_V"] = round(float(np.median([m["ref_reset"] - np.mean(list(m["reset_level"].values())) for m in p1])), 4)
    (S / "phase3A_T.json").write_text(json.dumps(res, indent=1, default=float))
    return res


def phase3B(phase="phase3B", prefix="B_sv", levels=None, assumption=None):
    import phase3 as P
    levels = P.B_SIG_MV if levels is None else levels
    assumption = assumption or "sigma_Vth per device (geometry-independent), sigma_mu/mu 10 %, R_C lognormal 20 %"
    runs = load(phase); res = {}
    for s in levels:
        dies = {}
        for d in P.B_DIES:
            rs = [m for m in runs if m["tag"].startswith(f"{prefix}{s:02d}_d{d}_")]
            if rs:
                dies[d] = acc_block(rs)
                pc = [m["winner"] for m in rs if m.get("valid")]
                if pc:   # class bias of the die: share of valid predictions that go to its most frequent class
                    top = max(set(pc), key=pc.count)
                    dies[d]["dominant_class"] = top
                    dies[d]["dominant_class_share"] = round(pc.count(top) / len(pc), 4)
        accs = [b["accuracy"] for b in dies.values() if b["n"] == len(P.SUB)]
        vals = [b["validity"] for b in dies.values() if b["n"] == len(P.SUB)]
        res[f"{'anchor' if prefix in ('P_an', 'V_an') else 'sigma_vth'}_{s}mV"] = dict(assumption=assumption,
                                       n_dies_complete=len(accs), accuracy_median=float(np.median(accs)) if accs else None,
                                       accuracy_worst_die=min(accs) if accs else None, accuracy_best_die=max(accs) if accs else None,
                                       validity_median=float(np.median(vals)) if vals else None, validity_worst_die=min(vals) if vals else None,
                                       dominant_class_share_median=float(np.median([b["dominant_class_share"] for b in dies.values() if "dominant_class_share" in b])) if dies else None,
                                       pooled=acc_block([m for m in runs if m["tag"].startswith(f"{prefix}{s:02d}_")]), dies=dies)
    (S / f"{phase}.json").write_text(json.dumps(res, indent=1, default=float))
    return res


def phase3B_V():
    """V_th-only size-scaled mismatch (D13), with per-die pairing to 3B-P (identical V_th draws) and to flat 20 mV."""
    import phase3 as P
    r = phase3B("phase3B_V", "V_an", P.V_ANCHOR_MV,
                "size-scaled V_th only: sigma_Vth = anchor * sqrt(780 um^2/(W*L)); mu and R_C nominal")
    v = {m["tag"][2:]: m for m in load("phase3B_V")}                       # key: anXX_dD_sII
    p = {m["tag"][2:]: m for m in load("phase3B_P")}
    f = {"an20" + m["tag"][len("B_sv20"):]: m for m in load("phase3B") if m["tag"].startswith("B_sv20_")}
    pairs = {}
    for name, other in (("vs_3BP_same_vth_draws", p), ("vs_flat20_same_random_numbers", f)):
        keys = sorted(set(v) & set(other))
        if keys:
            pairs[name] = dict(n=len(keys), v_correct=sum(outcome(v[k]) == v[k]["label"] for k in keys),
                               other_correct=sum(outcome(other[k]) == other[k]["label"] for k in keys),
                               same_outcome=sum(outcome(v[k]) == outcome(other[k]) for k in keys),
                               v_valid=sum(bool(v[k].get("valid")) for k in keys), other_valid=sum(bool(other[k].get("valid")) for k in keys))
    r["pairs"] = pairs
    (S / "phase3B_V.json").write_text(json.dumps(r, indent=1, default=float))
    return r


def phase3B_P():
    import phase3 as P
    r = phase3B("phase3B_P", "P_an", P.P_ANCHOR_MV,
                "size-scaled (Pelgrom): sigma = anchor * sqrt(780 um^2/(W*L)) for V_th; 10 % and 20 % at 780 um^2 for mu and R_C")
    # paired comparison with the flat 20 mV dies (same seeds -> same underlying random numbers)
    flat = {m["tag"][len("B_sv20_"):]: m for m in load("phase3B") if m["tag"].startswith("B_sv20_")}
    pel = {m["tag"][len("P_an20_"):]: m for m in load("phase3B_P") if m["tag"].startswith("P_an20_")}
    keys = sorted(set(flat) & set(pel))
    if keys:
        r["paired_flat20_vs_anchor20"] = dict(n=len(keys), flat_correct=sum(outcome(flat[k]) == flat[k]["label"] for k in keys),
                                              pelgrom_correct=sum(outcome(pel[k]) == pel[k]["label"] for k in keys),
                                              same_outcome=sum(outcome(flat[k]) == outcome(pel[k]) for k in keys))
        (S / "phase3B_P.json").write_text(json.dumps(r, indent=1, default=float))
    return r


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for name, fn in (("phase1", phase1), ("chain", chain), ("phase3A", phase3A), ("phase3B", phase3B),
                     ("phase3A_T", phase3A_T), ("phase3B_P", phase3B_P), ("phase3B_V", phase3B_V)):
        if which in (name, "all"):
            r = fn()
            print(name, json.dumps({k: v for k, v in r.items() if k not in ("rows", "dies", "disagreements")}, default=float)[:1500])
