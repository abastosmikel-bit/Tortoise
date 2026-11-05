"""Variant 3 check (DECISIONS.md D9): #81 and #31, borrowed prior, 2500 us window. Gate B criteria (D6) + race < 1200 us
+ ref settled (|ref(309 us) - ref(308 us)| < 5 mV). Variant 1 values for comparison come from its saved runs
(raw/diag_window/v1w2500_*.json and the waveform csv). -> raw/gateB_v3/, summary/gateB_v3.json"""
import gzip, json
import numpy as np
from multiprocessing import Pool
import common as C
from gateB import PRIOR, check


def v1_ref(tag):
    f = C.CAMP / f"raw/diag_window/{tag}.csv.gz"
    h = gzip.open(f, "rt").readline().strip().split(","); d = np.loadtxt(f, delimiter=",", skiprows=1)
    t, r = d[:, 0], d[:, h.index("ref")]
    return dict(ref_308=round(float(np.interp(308, t, r)), 5), ref_309=round(float(np.interp(309, t, r)), 5),
                ref_settle_mV_308_309=round(float(np.interp(309, t, r) - np.interp(308, t, r)) * 1e3, 3))


if __name__ == "__main__":
    jobs = [dict(tag=f"v3_s{i}", idx=i, prior=PRIOR, variant=3, outdir=C.CAMP / "raw/gateB_v3", wdir="gateB3") for i in (81, 31)]
    with Pool(2) as p:
        res = p.map(C.run_one, jobs)
    out = {}
    for m in res:
        race = min(m["trip_us"].values()) - m["tC2_us"] if m.get("trip_us") else None
        crit = dict(check(m, m["idx"]), race_lt_1200us=race is not None and race < 1200,
                    ref_settled_lt_5mV=abs(m["ref_settle_mV_308_309"]) < 5)
        v1 = json.load(open(C.CAMP / f"raw/diag_window/v1w2500_s{m['idx']}.json"))
        out[m["tag"]] = dict(criteria=crit, passed=all(crit.values()), race_time_from_C2_us=round(race, 3) if race else None,
                             **{k: m.get(k) for k in ("label", "trip_us", "latched", "valid", "failure", "lock_latency_us", "lockb_chain_us",
                                                       "runner_up", "gap", "ref_reset", "ref_308", "ref_309", "ref_settle_mV_308_309",
                                                       "reset_level", "rail_at_C2", "resized", "run")},
                             variant1=dict(race_time_from_C2_us=round(min(v1["trip_us"].values()) - v1["tC2_us"], 3), ref_reset=v1["ref_reset"],
                                           latched=v1["latched"], lock_latency_us=v1["lock_latency_us"], gap=v1["gap"], **v1_ref(f"v1w2500_s{m['idx']}")))
    out["passed_all"] = all(v["passed"] for k, v in out.items() if k.startswith("v3"))
    (C.CAMP / "summary/gateB_v3.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))
