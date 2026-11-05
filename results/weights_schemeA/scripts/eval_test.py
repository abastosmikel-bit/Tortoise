"""A2 (DECISIONS.md W10): the single test-set evaluation of a frozen weight set.
Usage: python3 eval_test.py run <FINAL_name> [nproc]     90 independent test runs + the chain (test 30..39 in sequence)
       python3 eval_test.py summary <FINAL_name>         -> summary/A2_<FINAL_name>.json, summary/A2_<FINAL_name>_runs.csv
Guard: refuses to run unless weights/<FINAL_name>.npy matches the sha256 in weights/FROZEN.json (frozen and committed
before any test run). Warm start: the weight set's own W6 warm start (training sample). The old weights' per-sample
results come from the campaign's Variant 3 Phase 1 (results/fitc10_campaign/raw/v3/phase1), read only here.
Paired comparison: exact two-sided McNemar test on the discordant pairs."""
import csv, hashlib, json, math, subprocess, sys
import numpy as np
import wcommon as W
import surrogate as SG
import runs as R

CHAIN = list(range(30, 40))


def frozen(name):
    fro = json.loads((W.WEIGHTS / "FROZEN.json").read_text())[name]
    f = W.WEIGHTS / f"{name}.npy"
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    assert sha == fro["sha256"], "weights changed after freezing"
    # committed at HEAD with identical content (audit finding 6: `git ls-files` alone also accepts a staged file)
    rel = str(f.relative_to(W.REPO))
    blob = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=W.REPO, capture_output=True)
    assert blob.returncode == 0 and hashlib.sha256(blob.stdout).hexdigest() == sha, "frozen weights must be committed (at HEAD) before the test run"
    return W.load_F(f), fro


def run(name, nproc):
    F, fro = frozen(name)
    timing = fro.get("timing")
    prior = W.pathlib.Path(fro["warm_start"])          # the source candidate's own W6 warm start (training sample)
    assert prior.with_suffix(".dat").exists(), "warm start missing"
    out = W.RAW / f"test_{name}"
    jobs = [dict(tag=f"s{i:02d}", split="test", idx=i, F=F, weights_name=name, prior=prior, outdir=out, wdir=f"wsA_test_{name}",
                 timing=timing) for i in range(90)]
    R.run_pool(jobs, nproc)
    cout = W.RAW / f"chain_{name}"
    p = prior
    for i in CHAIN:
        tag = f"c{i:02d}"
        if not (cout / f"{tag}.json").exists():
            W.run_one(dict(tag=tag, split="test", idx=i, F=F, weights_name=name, prior=p, outdir=cout, wdir=f"wsA_chain_{name}",
                           timing=timing, save_prior=cout / f"{tag}_end"))
        p = cout / f"{tag}_end"


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def outcome(m):
    return m["winner"] if m.get("valid") else None


def pct(x, qs=(0, 5, 25, 50, 75, 95, 100)):
    x = np.asarray([v for v in x if v is not None], float)
    return {f"p{q}": round(float(np.percentile(x, q)), 3) for q in qs} if len(x) else {}


def summary(name):
    F, fro = frozen(name)
    runs = sorted(W.load_runs(f"test_{name}"), key=lambda m: m["idx"])
    assert len(runs) == 90 and all(m["split"] == "test" for m in runs)
    old = {}
    for i in range(90):
        old[i] = json.loads((W.CAMP / f"raw/v3/phase1/s{i:02d}.json").read_text())
    q = SG.corner_params(0.65, fro.get("timing"))
    X, y = W.XTE, W.YTE
    w, gap, ru, c1 = SG.predict(F, X, q)
    rows = []
    for m in runs:
        i = m["idx"]; g = m.get("gap") or {}
        rows.append(dict(idx=i, label=m["label"], spice_class=outcome(m) or "", valid=m["valid"], failure=m.get("failure") or "",
                         first=m.get("first") or "", latched=";".join(map(str, m.get("latched") or [])), runner_up=m.get("runner_up") or "",
                         gap_reach_us=g.get("gap_reach_us"), gap_dV_mV=g.get("dV_mV"), lock_latency_us=m.get("lock_latency_us"),
                         trip_in_C1=m.get("trip_in_C1"), race_from_C2_us=round(min(m["trip_us"].values()) - m["tC2_us"], 3) if m.get("trip_us") else None,
                         sur_first=int(w[0, i]) + 1, sur_runner_up=int(ru[0, i]) + 1, sur_gap_us=round(float(gap[0, i]), 3),
                         sur_correct=bool(int(w[0, i]) == y[i] and gap[0, i] >= q["G_res"] and not c1[0, i]),
                         sw_class=int(np.argmax(X[i] @ F)) + 1,
                         old_class=outcome(old[i]) or "", old_valid=old[i]["valid"], old_correct=outcome(old[i]) == old[i]["label"]))
    with open(W.SUMM / f"A2_{name}_runs.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)
    n = 90
    k = sum(1 for r in rows if r["spice_class"] == r["label"]); nv = sum(1 for r in rows if r["valid"])
    ko = sum(1 for r in rows if r["old_correct"])
    cm = np.zeros((5, 6), int)
    for r in rows:
        cm[r["label"] - 1, (r["spice_class"] - 1) if r["spice_class"] else 5] += 1
    b = sum(1 for r in rows if r["old_correct"] and r["spice_class"] != r["label"])
    c = sum(1 for r in rows if not r["old_correct"] and r["spice_class"] == r["label"])
    fails = {}
    for r in rows:
        if not r["valid"]:
            fails[r["failure"]] = fails.get(r["failure"], 0) + 1
    v = [r for r in rows if r["valid"]]
    gaps = [r["gap_reach_us"] for r in v]
    same = [(r["sur_gap_us"], r["gap_reach_us"]) for r in v if r["gap_reach_us"] is not None and r["sur_first"] == r["first"] and r["sur_runner_up"] == r["runner_up"]]
    a_, b_ = np.array(same).T
    ch = {m["idx"]: m for m in W.load_runs(f"chain_{name}")}
    ind = {m["idx"]: m for m in runs}
    chain_rows = []
    for i in CHAIN:
        if i in ch:
            cc, dd = ch[i], ind[i]
            ft = lambda m: min(m["trip_us"].values()) if m.get("trip_us") else None
            chain_rows.append(dict(idx=i, label=cc["label"], chain_class=outcome(cc), indep_class=outcome(dd),
                                   same_outcome=outcome(cc) == outcome(dd) and cc["valid"] == dd["valid"],
                                   d_first_trip_us=round(ft(cc) - ft(dd), 3) if ft(cc) and ft(dd) else None,
                                   d_gap_us=round(cc["gap"]["gap_reach_us"] - dd["gap"]["gap_reach_us"], 3)
                                   if cc.get("gap") and dd.get("gap") and cc["gap"].get("gap_reach_us") is not None and dd["gap"].get("gap_reach_us") is not None else None,
                                   d_reset_level_mV_max=round(max(abs(cc["reset_level"][kk] - dd["reset_level"][kk]) for kk in cc["reset_level"]) * 1e3, 3)))
    res = dict(weights=name, F=F.tolist(), n_tft=runs[0]["n_tft"], banks=int((F > 0).sum()), timing=fro.get("timing"),
               accuracy=dict(correct=k, n=n, value=round(k / n, 4), wilson95=W.wilson(k, n)),
               validity=dict(valid=nv, n=n, value=round(nv / n, 4), wilson95=W.wilson(nv, n)), failures=fails,
               confusion=dict(rows="label 1..5", cols="SPICE class 1..5, invalid", matrix=cm.tolist()),
               software_argmax_accuracy=round(float(np.mean(np.argmax(X @ F, 1) == y)), 4),
               surrogate=dict(accuracy=round(float(np.mean([r["sur_correct"] for r in rows])), 4),
                              first_agree=sum(1 for r in rows if r["sur_first"] == r["first"]),
                              correct_agree=sum(1 for r in rows if r["sur_correct"] == (r["spice_class"] == r["label"])),
                              gap_pairs=len(same), gap_pearson_r=round(float(np.corrcoef(a_, b_)[0, 1]), 4),
                              gap_ratio_spice_over_sur_median=round(float(np.median(b_ / a_)), 4)),
               gap_reach_us=pct(gaps), gap_dV_mV=pct([r["gap_dV_mV"] for r in v]),
               lock_latency_us=pct([r["lock_latency_us"] for r in v]), race_from_C2_us=pct([r["race_from_C2_us"] for r in rows]),
               n_trip_in_C1=sum(1 for r in rows if r["trip_in_C1"]), n_gap_below_20us=sum(1 for g in gaps if g is not None and g < 20),
               old_weights=dict(correct=ko, n=n, value=round(ko / n, 4), wilson95=W.wilson(ko, n),
                                source="results/fitc10_campaign/raw/v3/phase1 (old weights, #81-derived warm start)"),
               paired=dict(both_correct=sum(1 for r in rows if r["old_correct"] and r["spice_class"] == r["label"]),
                           old_only=b, new_only=c, both_wrong=sum(1 for r in rows if not r["old_correct"] and r["spice_class"] != r["label"]),
                           mcnemar_exact_two_sided_p=round(mcnemar_exact(b, c), 4), difference=round((k - ko) / n, 4)),
               chain=dict(n=len(chain_rows), n_same_outcome=sum(r["same_outcome"] for r in chain_rows), rows=chain_rows,
                          correct=sum(1 for i in CHAIN if i in ch and outcome(ch[i]) == ch[i]["label"])))
    # the old weights' Phase 1 runs, summarised with the same definitions (campaign raw per-run JSONs)
    ov = [old[i] for i in range(90) if old[i].get("valid")]
    ofails = {}
    for i in range(90):
        if not old[i].get("valid"):
            ofails[old[i].get("failure")] = ofails.get(old[i].get("failure"), 0) + 1
    ocm = np.zeros((5, 6), int)
    for i in range(90):
        ocm[old[i]["label"] - 1, (outcome(old[i]) - 1) if outcome(old[i]) else 5] += 1
    nv_old = len(ov)
    res["old_weights"].update(validity=dict(valid=nv_old, n=n, value=round(nv_old / n, 4), wilson95=W.wilson(nv_old, n)), failures=ofails,
                              software_argmax_accuracy=round(float(np.mean(np.argmax(X @ W.F_OLD, 1) == y)), 4),
                              gap_reach_us=pct([(m.get("gap") or {}).get("gap_reach_us") for m in ov]),
                              lock_latency_us=pct([m.get("lock_latency_us") for m in ov]),
                              race_from_C2_us=pct([min(m["trip_us"].values()) - m["tC2_us"] for m in old.values() if m.get("trip_us")]),
                              n_trip_in_C1=sum(1 for m in old.values() if m.get("trip_in_C1")),
                              n_gap_below_20us=sum(1 for m in ov if (m.get("gap") or {}).get("gap_reach_us") is not None and m["gap"]["gap_reach_us"] < 20),
                              confusion=ocm.tolist(), n_tft=old[0]["n_tft"])
    (W.SUMM / f"A2_{name}.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({kk: vv for kk, vv in res.items() if kk != "chain"}, indent=1, default=float))
    return res


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 4)
    else:
        summary(sys.argv[2])
