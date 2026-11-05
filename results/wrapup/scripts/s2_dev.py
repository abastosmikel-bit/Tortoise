"""Study 2 development screen (DECISIONS S2.0; development, not a result): Tortoise v1.0 and four candidate resizes, one
TRAINING sample (#123, class 5; the weight-retraining study's warm-start sample), |V_th| 0.45 and 0.49 V in mode W and 0.65 V in mode G,
levels from the true |V_th| (V1 = 3.3 - |V_th| - 0.83, V2 = 3.3 - |V_th| - 0.25), k = 1, start states borrowed from the
Tortoise v1.0 calibrations (host_v21 cal v0490_m100 for mode W, host_v2 cal v0650_m100 for mode G). No test sample is used.
Usage: python3 s2_dev.py [nproc]  -> raw/S2dev/*.json, summary/s2_dev.json"""
import json, sys
import numpy as np
import wu, hv2, common as C
import s2_variants as V

IDX = 123


def jobs():
    stW = json.load(open(wu.HV21RAW / "cal/v0490_m100/calibration.json"))["start_state"]
    stG = json.load(open(wu.HV2RAW / "cal/v0650_m100/calibration.json"))["start_state"]
    x = C.D["X_train"][IDX]
    lab = int(C.D["y_train"][IDX]) + 1
    out = []
    for var in [None] + [v for v in V.CANDIDATES if v in (sys.argv[2:] or V.CANDIDATES)]:
        for vth, mode, st in ((0.45, "W", stW), (0.49, "W", stW), (0.65, "G", stG)):
            V1, V2 = hv2.levels(vth)
            out.append(dict(tag=f"S2dev_{var or 'R10.1'}_v{round(vth*1000):04d}_tr{IDX}", idx=None, x=x, label=lab,
                            outdir=wu.RAW / "S2dev", wdir="wu_S2dev", vth=vth, muf=1.0, mc=None, V1=V1, V2=V2, k=1.0,
                            mode=mode, prior_state=st, vth_metric=vth, variant=var, policy="dev"))
    return out


def summary():
    rows = []
    for j in jobs():
        m = json.load(open(wu.RAW / "S2dev" / f"{j['tag']}.json"))
        rows.append(dict(tag=m["tag"], variant=j["variant"] or "R10.1", vth=j["vth"], mode=j["mode"],
                         read=m.get("latched_read"), failure=m.get("failure_read"), race_us=m.get("race_us"),
                         t_read_us=m.get("t_read_us"), first=m.get("first"), label=j["label"]))
    json.dump(rows, open(wu.SUMM / "s2_dev.json", "w"), indent=1)
    for r in rows:
        print(r)


if __name__ == "__main__":
    n = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 2
    if sys.argv[1:2] == ["summary"]:
        sys.argv = sys.argv[:1]
        summary()
    else:
        wu.pool_run(jobs(), n)
        summary()
