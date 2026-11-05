"""B1.5: host-only energy options (DECISIONS E3), each on all 90 test samples, instrumented, next to the baseline.
 O1  adaptive race end: rows back to 3.3 V 50 us after the first output edge; outputs read 10 us later; the next
     classification starts there (back-to-back, VDD on). Own warm start by the D7 procedure (#81 chained with O1).
 O2  VDD power-gated idle: cold start every classification (all nodes and lines at 0 V), baseline 2500 us window.
 O12 O1 + O2: cold start, adaptive end (VDD switched off after the outputs are read).
Usage: python3 b1_options.py chain|O1|O2|O12 [nproc]   -> raw/b1_opt_<opt>/"""
import json, sys
import eh

D_US = 50.0
OUT = {o: eh.RAW / f"b1_opt_{o}" for o in ("O1", "O2", "O12")}
CHAIN = eh.RAW / "b1_opt_O1_chain"
O1_WARM = CHAIN / "O1_warm"


def chain():
    f = eh.SUMM / "b1_opt_O1_chain.json"
    if f.exists() and json.load(open(f))["converged"] and (CHAIN / "O1_warm.dat").exists():
        print("chain already converged", flush=True)
        return
    prior, hist = eh.WARM, []
    for k in range(1, 11):
        tag = f"c{k:02d}_s81"
        m = eh.run(dict(tag=tag, idx=81, outdir=CHAIN, wdir="b1c", prior=prior, adaptive=D_US, save_prior=CHAIN / f"{tag}_end"))
        rl = m["reset_level"]
        d = max(abs(rl[i] - hist[-1]["reset_level"][i]) for i in rl) * 1e3 if hist else None
        hist.append(dict(run=k, tag=tag, prior=str(prior), reset_level=rl, ref_reset=m["ref_reset"], max_delta_mV=d,
                         latched=m.get("latched"), latched_at_cls=m.get("latched_at_cls"), trip_us=m.get("trip_us")))
        print(json.dumps(hist[-1], default=float), flush=True)
        prior = CHAIN / f"{tag}_end"
        if d is not None and d < 5.0:
            break
    for ext in (".dat", ".cols"):
        (CHAIN / f"O1_warm{ext}").write_bytes((CHAIN / f"{prior.name}{ext}").read_bytes())
    json.dump(dict(converged=hist[-1]["max_delta_mV"] is not None and hist[-1]["max_delta_mV"] < 5.0, runs=hist),
              open(eh.SUMM / "b1_opt_O1_chain.json", "w"), indent=1, default=float)


def jobs(opt):
    base = dict(O1=dict(adaptive=D_US, prior=O1_WARM), O2=dict(cold=True), O12=dict(cold=True, adaptive=D_US))[opt]
    return [dict(tag=f"{opt}_s{i:02d}", idx=i, outdir=OUT[opt], wdir=f"b1{opt}", **base) for i in range(90)]


if __name__ == "__main__":
    w = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    if w == "chain":
        chain()
    else:
        eh.pool_run(jobs(w), n)
