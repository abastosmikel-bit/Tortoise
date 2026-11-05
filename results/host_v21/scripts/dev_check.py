"""Pre-freeze tooling check (development, not a result): mode G through hv21.run_cls must reproduce a finished v2 run
(host_v2 C3 cell 0.65 V / mu x1, sample #81 is not in the subset, so the first subset sample s01 is used)."""
import json
import hv21, hv2
src = json.load(open(hv21.HV2 / "raw/C3/C3_v0650_m100_learned_s01.json"))
j = src["job"]
m = hv21.run_cls(dict(tag="dev_G_repro_s01", outdir=hv21.RAW / "dev", idx=1, vth=0.65, muf=1.0, V1=j["V1"], V2=j["V2"],
                      k=j["k"], mode="G", prior_state=src["prior_state"], vth_metric=0.65))
keys = ("race_us", "latched_read", "failure_read", "t_read_us", "lock_us")
out = {k: (src.get(k), m.get(k)) for k in keys}
out["same"] = all(str(a) == str(b) for a, b in out.values())
print(json.dumps(out, indent=1))
json.dump(out, open(hv21.RAW / "dev/dev_G_repro_check.json", "w"), indent=1)
