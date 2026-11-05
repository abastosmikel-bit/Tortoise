"""H1.6: start-state convergence. #81 chained 3 times (classification -> 1 s VDD-off -> classification ...) from the
nominal design-time calibration's start state, nominal levels, k = 1. Development run (raw/dev/)."""
import json
import hv2
c = json.load(open(hv2.RAW / "cal/design_nominal/calibration.json"))
st, hist = c["start_state"], []
for n in range(3):
    m = hv2.run_cls(dict(tag=f"devchain_{n}_s81", idx=81, outdir=hv2.RAW / "dev", wdir="devc", V1=1.82, V2=2.40, k=1.0,
                         prior_state=st, vth_metric=0.65, save_wave=False))
    hist.append(dict(step=n, start=st, reset_level=m["reset_level"], ref_reset=m["ref_reset"], race=m["race_us"],
                     read=m["latched_read"], failure=m["failure_read"]))
    print(n, m["latched_read"], m["race_us"], list(m["reset_level"].values())[0], m["ref_reset"], {k: round(v, 3) for k, v in st.items() if k[:2] in ("ap", "na", "re")}, flush=True)
    st = hv2.off_state(f"devchain_{n}_off", hv2.RAW / "dev", m["end_state_read"], 0.65, 1.0, None)
json.dump(hist, open(hv2.SUMM / "dev_chain.json", "w"), indent=1, default=float)
