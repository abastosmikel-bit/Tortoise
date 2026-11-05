"""W9: SPICE decision between the top candidates on the held-out selection set S (40 training samples, 4 groups).
Usage: python3 select_spice.py run <name> [<name> ...]   W6 warm start + 40 nominal S runs per weight set (weights/<name>.npy)
       python3 select_spice.py decide <name> [<name> ...]  apply the W9 rule, freeze weights/FINAL_frozen.npy (+ FROZEN.json)
       python3 select_spice.py summary <name> [<name> ...] recompute summary/A1_select.json only (checks it agrees with FROZEN.json)
Winner = highest SPICE accuracy on S (invalid = wrong); tie -> higher CV score S (summary/A1_cv.json). The old weights
(raw/S_old) are shown as a reference only.
-> summary/A1_select.json, weights/FINAL_frozen.npy, weights/FROZEN.json"""
import hashlib, json, sys
import numpy as np
import wcommon as W
import surrogate as SG
import runs as R
from calib_fit import agreement

SPL = json.loads((W.SUMM / "splits.json").read_text())


def summarize(name):
    rs = W.load_runs(f"S_{name}")
    assert len(rs) == 40 and all(m["split"] == "train" and m["idx"] in SPL["S"] for m in rs), (name, len(rs))
    k = sum(1 for m in rs if m.get("valid") and m["winner"] == m["label"])
    nv = sum(1 for m in rs if m.get("valid"))
    ag = agreement(rs, SG.corner_params(0.65))
    return dict(n=len(rs), correct=k, accuracy=k / len(rs), wilson95=W.wilson(k, len(rs)), valid=nv,
                failures=[dict(idx=m["idx"], failure=m.get("failure"), latched=m.get("latched"), gap=(m.get("gap") or {}).get("gap_reach_us")) for m in rs if not m.get("valid")],
                per_sample={m["idx"]: bool(m.get("valid") and m["winner"] == m["label"]) for m in rs},
                surrogate_agreement={kk: v for kk, v in ag.items() if kk != "rows"}, n_tft=rs[0]["n_tft"],
                race_from_C2_median_us=float(np.median([min(m["trip_us"].values()) - m["tC2_us"] for m in rs if m.get("trip_us")])),
                lock_latency_median_us=float(np.median([m["lock_latency_us"] for m in rs if m.get("valid")])))


if __name__ == "__main__":
    mode, names = sys.argv[1], sys.argv[2:]
    if mode == "run":
        for n in names:
            if not (W.SUMM / f"warm_{n}.json").exists():
                R.warm(n)
            R.run_pool(R.nominal_jobs(n, SPL["S"], "S"), 4)
        sys.exit()
    cv = json.loads((W.SUMM / "A1_cv.json").read_text())["best_per_family"]
    res = {"old (reference)": summarize("old")}
    for n in names:
        res[n] = summarize(n)
        fam = n.split("_")[-1]
        res[n]["cv"] = cv.get(fam)
        res[n]["F"] = W.load_F(W.WEIGHTS / f"{n}.npy").tolist()
    # pairwise per-sample comparison with the old weights on S
    for n in names:
        a, b = res["old (reference)"]["per_sample"], res[n]["per_sample"]
        res[n]["vs_old_on_S"] = dict(both=sum(a[i] and b[i] for i in a), old_only=sum(a[i] and not b[i] for i in a),
                                     new_only=sum(b[i] and not a[i] for i in a), neither=sum(not a[i] and not b[i] for i in a))
    win = max(names, key=lambda n: (res[n]["correct"], res[n]["cv"]["S"] if res[n].get("cv") else -1))
    if mode == "summary":                 # recompute A1_select.json only; never touches the frozen weights (post-audit)
        fro = json.loads((W.WEIGHTS / "FROZEN.json").read_text())["FINAL_frozen"]
        assert fro["source"] == f"weights/{win}.npy", (fro["source"], win)
        (W.SUMM / "A1_select.json").write_text(json.dumps(dict(candidates=names, winner=win, results=res), indent=1, default=float))
        print("A1_select.json recomputed; winner", win); sys.exit()
    F = W.load_F(W.WEIGHTS / f"{win}.npy")
    np.save(W.WEIGHTS / "FINAL_frozen.npy", F)
    sha = hashlib.sha256((W.WEIGHTS / "FINAL_frozen.npy").read_bytes()).hexdigest()
    fro = json.loads((W.WEIGHTS / "FROZEN.json").read_text()) if (W.WEIGHTS / "FROZEN.json").exists() else {}
    fro["FINAL_frozen"] = dict(source=f"weights/{win}.npy", sha256=sha, F=F.tolist(), banks=int((F > 0).sum()), n_tft=W.n_tft(F),
                               warm_start=str(R.warm_prior(win)), timing=None,
                               rule="W9: highest SPICE accuracy on S; tie -> higher CV score S")
    (W.WEIGHTS / "FROZEN.json").write_text(json.dumps(fro, indent=1))
    out = dict(candidates=names, winner=win, results=res)
    (W.SUMM / "A1_select.json").write_text(json.dumps(out, indent=1, default=float))
    for n, r in res.items():
        print(f"{n:20s} S-set SPICE {r['correct']}/40 valid {r['valid']}/40 agree(first) {r['surrogate_agreement']['first_agree']}/40 "
              f"sur_correct {r['surrogate_agreement']['sur_correct']} {r.get('vs_old_on_S', '')}")
    print("winner", win, F.tolist(), sha)
