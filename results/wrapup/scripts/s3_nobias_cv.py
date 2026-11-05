"""Post-hoc analysis (disclosed in REPORT §3; training data only, after the CV and selection): the selected config
(le60, m = 30 us) trained on the same 20 group splits of T with the SAME recalibrated v2.1 surrogate but the bias row
forced empty (F_b = 0, input banks <= 21, i.e. the Tortoise v1.0 crossbar form). Isolates what the bias row adds in CV.
-> summary/s3_nobias_cv.json"""
import json
import numpy as np
import s3_train as TR

_moves = TR.moves


def moves_nobias(F6, Fb, mode, bud):
    for G, H in _moves(F6, Fb, mode, bud):
        if (np.asarray(H) == 0).all():
            yield G, H


TR.moves = moves_nobias
q = TR.params()
dies = TR.eval_dies()
rows = []
for k, sp in enumerate(TR.SPL["cv_T"]):
    tr, va = np.array(sp["train"]), np.array(sp["val"])
    X, y = TR.W.XTR[tr], TR.W.YTR[tr]
    best = None
    for lam in (1e-4, 1e-3, 1e-2):
        F6, _ = TR.lr_start(X, y, lam, "b138")
        Fb = np.zeros(5, int)
        F6, Fb, v = TR.descend(F6, Fb, X, y, q, 30, "le60", "b138")
        if best is None or v > best[0] + 1e-12:
            best = (v, F6, Fb)
    sc = TR.score(best[1], best[2], TR.W.XTR[va], TR.W.YTR[va], q, dies)
    with_bias = json.load(open(TR.JOBS / f"le60_m30_b138_{k:02d}.json"))
    rows.append(dict(split=k, nobias=sc, bias=dict(A_nom=with_bias["A_nom"], A_mm=with_bias["A_mm"], S3=with_bias["S3"])))
    print(k, {a: round(b, 3) for a, b in sc.items()}, round(with_bias["S3"], 3), flush=True)
m = lambda key, kind: float(np.mean([r[kind][key] for r in rows]))
out = dict(config="le60_m30", splits=len(rows), nobias={k: m(k, "nobias") for k in ("A_nom", "A_mm", "S3")},
           bias={k: m(k, "bias") for k in ("A_nom", "A_mm", "S3")},
           paired_diff_A_nom=dict(mean=float(np.mean([r["bias"]["A_nom"] - r["nobias"]["A_nom"] for r in rows])),
                                  sd=float(np.std([r["bias"]["A_nom"] - r["nobias"]["A_nom"] for r in rows])),
                                  splits_bias_better=sum(r["bias"]["A_nom"] > r["nobias"]["A_nom"] for r in rows),
                                  splits_equal=sum(r["bias"]["A_nom"] == r["nobias"]["A_nom"] for r in rows)),
           rows=rows, note="post-hoc, training data only; not used for any selection")
json.dump(out, open(TR.WU / "summary/s3_nobias_cv.json", "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))
