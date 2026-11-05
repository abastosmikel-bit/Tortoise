"""Check that the *_mc model files with zero spread (DVTH=0, KMU=1, KRC=1 on every TFT) reproduce the nominal
Variant 1 run of #81 (borrowed prior, 2500 us window; reference summary/diag_window_v1.json). -> summary/mc_equiv.json"""
import json
import common as C
from gateB import PRIOR

if __name__ == "__main__":
    m = C.run_one(dict(tag="mc0_s81", idx=81, prior=PRIOR, variant=1, outdir=C.CAMP / "raw/mc_equiv", wdir="mceq",
                       mc=dict(seed=0, s_vth=0.0, s_mu=0.0, s_rc=0.0)))
    ref = json.load(open(C.CAMP / "summary/diag_window_v1.json"))["v1w2500_s81"]
    keys = ("trip_us", "latched", "lock_latency_us", "runner_up", "gap")
    out = dict(mc_zero={k: m.get(k) for k in keys}, nominal={k: ref.get(k) for k in keys})
    out["identical"] = all(json.dumps(out["mc_zero"][k], default=float) == json.dumps(out["nominal"][k], default=float) for k in keys)
    (C.CAMP / "summary/mc_equiv.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))
