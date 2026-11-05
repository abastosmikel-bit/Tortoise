"""Probe (training data only, nominal surrogate): does allowing column sums below 60 help? For each of the 20 CV
splits of T: start from the rounded constrained LR, greedy descent on the nominal surrogate's exact count (m = 0 and
m = 20 us) with column sums fixed at 60 vs free in [45, 60]; validation accuracy (nominal surrogate).
Run on 2026-10-25 after the K calibration and before any candidate training, to decide amendment W1.2b.
-> summary/A1_colsum_probe.json"""
import json
import numpy as np
from multiprocessing import Pool
import wcommon as W, optim as O, surrogate as SG
from obj import RaceObjective, descend

SPL = json.loads((W.SUMM / "splits.json").read_text())


def one(k):
    sp = SPL["cv_T"][k]; tr, va = np.array(sp["train"]), np.array(sp["val"])
    q = SG.corner_params(0.65)
    Wt, _ = O.fit_lr(W.XTR[tr], W.YTR[tr], 1e-3, False, True); F0 = O.to_fingers(Wt)
    out = {}
    for m in (0, 20):
        obj = RaceObjective(W.XTR[tr], W.YTR[tr], [q], None, tau=0.0, m=m, tie=1e-3)
        for name, cs in (("eq60", (60, 60)), ("le60", (45, 60))):
            F, v = descend(obj, F0, colsum=cs)
            out[f"{name}_m{m}"] = dict(train=float(SG.accuracy(F, W.XTR[tr], W.YTR[tr], q)[0]), val=int((SG.margin(F, W.XTR[va], W.YTR[va], q)[0] >= 0).sum()),
                                       n=len(va), colsums=F.sum(0).tolist())
    out["start"] = dict(val=int((SG.margin(F0, W.XTR[va], W.YTR[va], q)[0] >= 0).sum()), n=len(va))
    out["old"] = dict(val=int((SG.margin(W.F_OLD, W.XTR[va], W.YTR[va], q)[0] >= 0).sum()), n=len(va))
    return k, out


if __name__ == "__main__":
    with Pool(2) as p:
        res = dict(p.map(one, range(len(SPL["cv_T"]))))
    summ = {}
    for key in res[0]:
        summ[key] = round(sum(r[key]["val"] for r in res.values()) / sum(r[key]["n"] for r in res.values()), 4)
        if "train" in res[0][key]:
            summ[key + "_train"] = round(float(np.mean([r[key]["train"] for r in res.values()])), 4)
    (W.SUMM / "A1_colsum_probe.json").write_text(json.dumps(dict(summary=summ, per_split=res), indent=1))
    print(json.dumps(summ, indent=1))
    print([r["le60_m20"]["colsums"] for r in list(res.values())[:6]])
