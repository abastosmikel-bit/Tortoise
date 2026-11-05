"""H1 pre-freeze interaction checks (DECISIONS H1). TRAINING samples only (the first training sample of each class),
global corners, no mismatch. These are development runs: they choose between protocol options before the freeze and
are reported as such (raw/dev/, summary/dev_checks.json). No test sample is used except #81 for the start-state chain
(the same sample v1 and the energy/host study used to build their warm starts).
Usage: python3 dev_checks.py A|B|chain [nproc]"""
import json, sys
import numpy as np
import hv2, common as C

OUT = hv2.RAW / "dev"
TR = [int(np.where(C.D["y_train"] == c)[0][0]) for c in range(5)]   # first training sample of each class


def tj(tag, i, **kw):
    return dict(tag=f"{tag}_tr{i:03d}", x=C.D["X_train"][i], label=int(C.D["y_train"][i]) + 1, idx=None, outdir=OUT,
                wdir="dev", train_idx=i, **kw)


def off1s():
    return json.load(open(OUT / "dev_off_s81_10s.json"))["probe"]["1"]


def jobs(w):
    js = []
    for i in TR:
        if w == "A":   # nominal corner, k = 1: start state and rstb timing under power-gated cold start
            js += [tj("A_zero", i, k=1.0), tj("A_p1s", i, k=1.0, prior_state=off1s()),
                   tj("A_zero_rstb150", i, k=1.0, rstb_rel=None)]
        if w == "B":   # mu x0.5 at nominal |V_th|, k = 2: does D/READ need scaling? does the reset need scaling?
            js += [tj("B_k2_sd", i, muf=0.5, k=2.0, scale_d=True), tj("B_k2_nosd", i, muf=0.5, k=2.0, scale_d=False),
                   tj("B_k2_sd_noreset", i, muf=0.5, k=2.0, scale_d=True, scale_reset=False),
                   tj("B_k1", i, muf=0.5, k=1.0)]
    return js


if __name__ == "__main__":
    w = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    hv2.pool_run(hv2.run_cls, jobs(w), n)
