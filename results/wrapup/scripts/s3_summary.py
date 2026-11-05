"""Study 3 summaries (DECISIONS S3.2-S3.5), recomputed from per-run JSONs and CV job files.
Usage: python3 s3_summary.py cv      -> summary/s3_cv.json (CV table, finalists)       [training data only]
       python3 s3_summary.py select  -> summary/s3_select.json (SPICE on S, winner)    [training data only]
       python3 s3_summary.py eval    -> summary/s3_eval.json (test, mismatch, stress, TFTs, yield) [after the freeze]"""
import json, sys
import numpy as np
import wu
from s1_summary import block, correct, mcnemar, wilson, outcome

S = wu.SUMM


def cv():
    import s3_train as TR
    rows = {}
    for c in TR.CONFIGS:
        js = [json.load(open(TR.JOBS / f"{TR.cfg_name(c)}_{k:02d}.json")) for k in range(len(TR.SPL["cv_T"]))]
        rows[TR.cfg_name(c)] = dict(mode=c[0], m=c[1], budget=c[2], n_splits=len(js),
                                    S3=float(np.mean([j["S3"] for j in js])), S3_sd=float(np.std([j["S3"] for j in js])),
                                    A_nom=float(np.mean([j["A_nom"] for j in js])), A_mm=float(np.mean([j["A_mm"] for j in js])),
                                    tft_median=float(np.median([j["n_tft"] for j in js])),
                                    bias_banks_median=float(np.median([j["banks_bias"] for j in js])))
    best = {b: max((r for r in rows.values() if r["budget"] == b), key=lambda r: (r["S3"], -r["m"])) for b in TR.BUDGETS}
    fin = {b: [k for k, r in rows.items() if r is best[b]][0] for b in TR.BUDGETS}
    out = dict(configs=rows, finalists=fin, score="S3 = 0.5 A_nom + 0.5 A_mm (validation folds of the 20 group splits of T)")
    json.dump(out, open(S / "s3_cv.json", "w"), indent=1)
    for k, r in sorted(rows.items(), key=lambda kv: -kv[1]["S3"]):
        print(f"{k:22s} S3 {100*r['S3']:.1f} ({100*r['S3_sd']:.1f})  nom {100*r['A_nom']:.1f}  mm {100*r['A_mm']:.1f}  tft {r['tft_median']:.0f}")
    print("finalists:", fin)
    return out


def select():
    c = json.load(open(S / "s3_cv.json"))
    out = dict(finalists={})
    for b, cfg in c["finalists"].items():
        wn = f"S3_{cfg}"
        runs = [json.load(open(f)) for f in sorted((wu.RAW / "S3S").glob(f"S3S_{wn}_tr*.json"))]
        rec = json.load(open(wu.WU / "weights" / f"{wn}.json"))
        out["finalists"][wn] = dict(config=cfg, budget=b, cv_S3=c["configs"][cfg]["S3"], n_tft=rec["n_tft"], Fb=rec["Fb"],
                                    colsums=rec["colsums"], **block(runs))
    ws = sorted(out["finalists"], key=lambda w: (-out["finalists"][w]["correct"], -out["finalists"][w]["cv_S3"]))
    out["winner"] = ws[0]
    import s3_runs as R
    ref = [json.load(open(f)) for f in sorted((wu.REPO / "results/weights_schemeA/raw/S_old").glob("*.json")) if not f.name.endswith("_draws.json")]
    ref20 = [r for r in ref if r["idx"] in R.S20]
    out["reference_old_weights_v1_protocol"] = dict(note="Tortoise v1.0 weights on the same 20 S samples, v1 protocol (weight-retraining study A1 runs; "
                                                         "not v2.1, so not a paired comparison)", n=len(ref20),
                                                   correct=sum(bool(r.get("valid")) and r.get("winner") == r.get("label") for r in ref20))
    json.dump(out, open(S / "s3_select.json", "w"), indent=1)
    print(json.dumps(out, indent=1))
    return out


def evaluate():
    fz = json.load(open(wu.WU / "weights/FROZEN_S3.json"))
    wn = fz["weights"]
    rec = json.load(open(wu.WU / "weights" / f"{wn}.json"))
    out = dict(weights=wn, frozen=fz, n_tft=rec["n_tft"], Fb=rec["Fb"], F6=rec["F6"])
    runs = [json.load(open(wu.RAW / "S3test" / f"S3test_{wn}_s{i:02d}.json")) for i in range(90)]
    ref = [json.load(open(wu.HV2RAW / "C1" / f"C1_v0650_m100_learned_s{i:02d}.json")) for i in range(90)]
    A = [correct(r) for r in runs]; B = [correct(r) for r in ref]
    b = sum(x and not y for x, y in zip(A, B)); cc = sum(y and not x for x, y in zip(A, B))
    out["test"] = dict(**block(runs), validity_wilson95=wilson(sum(bool(r.get("valid_read")) for r in runs), 90),
                       rev10_1=block(ref), both=sum(x and y for x, y in zip(A, B)), bias_only=b, rev_only=cc,
                       neither=sum(not x and not y for x, y in zip(A, B)), mcnemar_p=mcnemar(b, cc),
                       gain_points=round(100 * (sum(A) - sum(B)) / 90, 1))
    out["test"]["reading"] = ("improves" if (b > cc and out["test"]["mcnemar_p"] < 0.05) else
                              ("worse" if (cc > b and out["test"]["mcnemar_p"] < 0.05) else "no resolvable change"))
    conf = {}
    for r in runs:
        conf.setdefault(str(r["label"]), {})
        k = str(r["winner_read"]) if r.get("valid_read") else "invalid"
        conf[str(r["label"])][k] = conf[str(r["label"])].get(k, 0) + 1
    out["test"]["confusion"] = conf
    mm, pairs = [], []
    import s3_runs as R
    for d in R.DIES:
        rr = [json.load(open(wu.RAW / "S3mm" / f"S3mm_{wn}_an20d{d['die']:02d}_s{i:02d}.json")) for i in wu.SUB]
        c4 = [json.load(open(wu.HV2RAW / "C4" / f"C4_v0650_m100_an20d{d['die']:02d}_learned_s{i:02d}.json")) for i in wu.SUB]
        mm += rr
        pairs += list(zip([correct(r) for r in rr], [correct(r) for r in c4]))
    b2 = sum(x and not y for x, y in pairs); c2 = sum(y and not x for x, y in pairs)
    out["mismatch"] = dict(**block(mm), C4_correct=sum(y for _, y in pairs), bias_only=b2, c4_only=c2, mcnemar_p=mcnemar(b2, c2))
    sf = S / f"s3_stress_{wn}.json"
    if sf.exists():
        s = json.load(open(sf))
        out["stress"] = dict(n_devices=s["n_devices"], n_above=s["n_above_any"], worst=s["worst"]["device"], worst_V=s["worst"]["max_stress"],
                             crossbar_max_V=s["crossbar_max"]["max_stress"], crossbar_max_device=s["crossbar_max"]["device"],
                             min_node_V=s["min_node_V"], min_node_V_off=s["min_node_V_off"])
    out["yield"] = dict(model="Y = 0.98^N (independent device failures)", rev10_1=0.98 ** 134, variant=0.98 ** rec["n_tft"],
                        ratio=0.98 ** (rec["n_tft"] - 134), extra_tft=rec["n_tft"] - 134)
    E = [r["energy_nJ"]["total"] for r in runs if "energy_nJ" in r]
    out["energy_nJ_median"] = round(float(np.median(E)), 1) if E else None
    out["energy_row7_nJ_median"] = round(float(np.median([r["energy_nJ"].get("VR7", 0.0) for r in runs])), 2)
    json.dump(out, open(S / "s3_eval.json", "w"), indent=1, default=float)
    print(json.dumps({k: v for k, v in out.items() if k not in ("F6", "frozen")}, indent=1, default=float))
    return out


if __name__ == "__main__":
    {"cv": cv, "select": select, "eval": evaluate}[sys.argv[1]]()
