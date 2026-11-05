"""Gate B: #81 and #31 at fitc10 with the borrowed prior t6L_x2_v085, criteria from DECISIONS.md D6.
Usage: python3 gateB.py <variant>   -> raw/gateB/v<variant>_s{81,31}.*, summary/gateB_v<variant>.json"""
import json, sys
from multiprocessing import Pool
import common as C

PRIOR = C.W / "sim/circuits/t6L_x2_v085"


def check(m, idx):
    ok = dict(valid=m.get("valid", False))
    if idx == 81:
        ok.update(latched_5=m.get("latched") == [5], no_C1_trip=not m.get("trip_in_C1", True),
                  lock_15_25us=m.get("lock_latency_us") is not None and 15 <= m["lock_latency_us"] <= 25)
    else:
        ok.update(latched_2=m.get("latched") == [2])
    return ok


if __name__ == "__main__":
    var = int(sys.argv[1])
    jobs = [dict(tag=f"v{var}_s{i}", idx=i, prior=PRIOR, variant=var, outdir=C.CAMP / "raw/gateB", wdir="gateB")
            for i in (81, 31)]
    with Pool(2) as p:
        res = p.map(C.run_one, jobs)
    out = {}
    for m in res:
        crit = check(m, m["idx"])
        out[m["tag"]] = dict(criteria=crit, passed=all(crit.values()),
                             **{k: m.get(k) for k in ("label", "trip_us", "first", "latched", "valid", "failure",
                                                       "lock_latency_us", "lockb_chain_us", "trip_in_C1", "runner_up",
                                                       "gap", "reset_level", "ref_reset", "rail_at_C2", "run")})
    out["gate_passed"] = all(v["passed"] for k, v in out.items() if k.startswith("v"))
    (C.CAMP / f"summary/gateB_v{var}.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))
