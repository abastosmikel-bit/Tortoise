"""DIAGNOSTIC ONLY (not a gate result): Variant 1, #81 and #31, borrowed prior, race window extended to
2500 us after C2 start (a simulation setting; the circuit is unchanged). Shows whether the rebuilt design
resolves the race correctly when given more time. -> raw/diag_window/, summary/diag_window_v1.json"""
import json
from multiprocessing import Pool
import common as C
from gateB import PRIOR, check

if __name__ == "__main__":
    jobs = [dict(tag=f"v1w2500_s{i}", idx=i, prior=PRIOR, variant=1, trace=2500.0,
                 outdir=C.CAMP / "raw/diag_window", wdir="diag") for i in (81, 31)]
    with Pool(2) as p:
        res = p.map(C.run_one, jobs)
    out = {m["tag"]: dict(criteria_as_gateB=check(m, m["idx"]),
                          **{k: m.get(k) for k in ("label", "trace_us", "t_end_us", "trip_us", "first", "latched",
                                                    "valid", "failure", "lock_latency_us", "lockb_chain_us",
                                                    "runner_up", "gap", "gaps", "ref_reset", "run")}) for m in res}
    (C.CAMP / "summary/diag_window_v1.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))
