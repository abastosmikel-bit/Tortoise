"""A1 CV selection metric (DECISIONS.md W8) on the 20 group splits of T. For every trained (family, config, split):
  A_nom  nominal-die surrogate accuracy at 0.65 V on the validation part
  A_mm   mean accuracy over the 500 evaluation dies (250 at 20 mV, 250 at 35 mV anchor; seed 41000) at 0.65 V
  A_rt   mean nominal-die accuracy over re-trimmed |V_th| 0.55/0.65/0.75/0.85/0.95 V (strict: trips in C1 fail)
  S = 0.5 A_nom + 0.25 A_mm + 0.25 A_rt
Pooled over the 20 splits (each of the 4 repeats covers all of T once); SD over the 4 repeats.
References (not candidates): old weights (in-sample: they were trained on all 210), and the circuit-unaware integer
classifier of A0 (int_ls, refit on each split's training part).
-> summary/A1_cv.json"""
import json, sys
import numpy as np
import wcommon as W
import surrogate as SG
from train import CONFIGS, MODES, VTH_GRID, JOBS, SPL, cfg_tag, parse_bc

FAMS = ("a", "b", "c")


def metrics(F, idx, dies, qs):
    X, y = W.XTR[idx], W.YTR[idx]
    q0 = qs["0.65"]
    nom = SG.margin(F, X, y, q0) >= 0
    mm = SG.margin(F, X, y, q0, dies) >= 0                          # (D, N)
    rt = np.stack([SG.margin(F, X, y, qs[f"{v:.2f}"])[0] >= 0 for v in VTH_GRID])   # (5, N)
    an = dies.anchor
    return dict(n=len(y), nom=int(nom.sum()), mm=float(mm.mean(0).sum()), mm20=float(mm[an < 0.03].mean(0).sum()),
                mm35=float(mm[an > 0.03].mean(0).sum()), rt=float(rt.mean(0).sum()),
                rt_by_vth={f"{v:.2f}": int(r.sum()) for v, r in zip(VTH_GRID, rt)})


def aggregate(rows):
    out = {}
    for key in ("nom", "mm", "mm20", "mm35", "rt"):
        reps = []
        for r in range(4):
            rr = [x for x in rows if SPL["cv_T"][x["split"]]["repeat"] == r]
            reps.append(sum(x[key] for x in rr) / sum(x["n"] for x in rr))
        out[f"A_{key}"] = round(float(np.mean(reps)), 4)
        out[f"A_{key}_sd_repeats"] = round(float(np.std(reps, ddof=1)), 4)
    S_reps = []
    for r in range(4):
        rr = [x for x in rows if SPL["cv_T"][x["split"]]["repeat"] == r]
        n = sum(x["n"] for x in rr)
        S_reps.append(0.5 * sum(x["nom"] for x in rr) / n + 0.25 * sum(x["mm"] for x in rr) / n + 0.25 * sum(x["rt"] for x in rr) / n)
    out["S"] = round(float(np.mean(S_reps)), 4); out["S_sd_repeats"] = round(float(np.std(S_reps, ddof=1)), 4)
    out["rt_by_vth"] = {v: round(sum(x["rt_by_vth"][v] for x in rows) / sum(x["n"] for x in rows), 4) for v in rows[0]["rt_by_vth"]}
    out["n_splits"] = len(rows)
    return out


if __name__ == "__main__":
    dies = SG.make_dies(250, (20, 35), 41000)
    qs = {f"{v:.2f}": SG.corner_params(v) for v in VTH_GRID}
    res = {"families": {}, "references": {}}
    for fam in FAMS:
      for mode in MODES:
        for cfg in CONFIGS[fam]:
            rows = []
            for k in range(len(SPL["cv_T"])):
                f = JOBS / f"{fam}_{mode}_{cfg_tag(cfg)}_{k:02d}.json"
                if not f.exists():
                    continue
                j = json.loads(f.read_text())
                m = metrics(np.array(j["F"]), np.array(SPL["cv_T"][k]["val"]), dies, qs)
                m.update(split=k, banks=j["banks"], colsum_min=int(np.array(j["F"]).sum(0).min())); rows.append(m)
            if len(rows) == len(SPL["cv_T"]):
                res["families"].setdefault(fam, {})[f"{mode}_{cfg_tag(cfg)}"] = dict(aggregate(rows), mode=mode, config=cfg_tag(cfg),
                                                                              banks_median=float(np.median([r["banks"] for r in rows])),
                                                                              colsum_min_median=float(np.median([r["colsum_min"] for r in rows])))
    # references
    rows = [dict(metrics(W.F_OLD, np.array(sp["val"]), dies, qs), split=k) for k, sp in enumerate(SPL["cv_T"])]
    res["references"]["old_weights_in_sample"] = aggregate(rows)
    if "--int" in sys.argv:
        import ceilings as CE
        rows = []
        for k, sp in enumerate(SPL["cv_T"]):
            tr = np.array(sp["train"])
            lam = CE.pick(tr, 7000 + k, CE.LAMS, lambda a, b, l: CE.lr_scores(a, b, l, False, True)[0])
            mu = CE.pick(tr, 7000 + k, CE.MUS, lambda a, b, u: W.XTR[b] @ CE.int_fit(a, u, lam)[1])
            F = CE.int_fit(tr, mu, lam)[1]
            rows.append(dict(metrics(F, np.array(sp["val"]), dies, qs), split=k))
        res["references"]["int_ls_circuit_unaware"] = aggregate(rows)
    best = {}
    for fam, d in res["families"].items():
        key = max(d, key=lambda c: (d[c]["S"], d[c]["mode"] == "eq60", -sum(parse_bc(d[c]["config"]))))   # ties: eq60, then smaller config
        best[fam] = dict(key=key, **d[key])
    res["best_per_family"] = best
    (W.SUMM / "A1_cv.json").write_text(json.dumps(res, indent=1))
    for fam, d in res["families"].items():
        for c, v in d.items():
            print(f"{fam} {c:>8s}: S {v['S']:.4f}±{v['S_sd_repeats']:.4f} nom {v['A_nom']:.4f} mm {v['A_mm']:.4f} (20 {v['A_mm20']:.4f} 35 {v['A_mm35']:.4f}) rt {v['A_rt']:.4f} {v['rt_by_vth']} banks {v['banks_median']} colsum_min {v['colsum_min_median']}")
    for n, v in res["references"].items():
        print(f"{n}: S {v['S']:.4f} nom {v['A_nom']:.4f} mm {v['A_mm']:.4f} rt {v['A_rt']:.4f} {v['rt_by_vth']}")
    print("best", {f: (b["key"], b["S"]) for f, b in best.items()})
