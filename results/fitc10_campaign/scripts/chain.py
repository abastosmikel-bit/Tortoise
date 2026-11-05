"""Phase 1.4: history-dependence chain. Test samples 30..39 run in sequence; run k starts from the end state of
run k-1 (the first from the fitc10 warm start), each with the normal host reset at the start of its cycle.
Compared with the independent Phase 1 runs (all from the same warm start).  -> raw/chain/c<idx>.*"""
import json
import common as C

WARM = C.RAW / "warmstart/fitc10_warm"
OUT = C.RAW / "chain"
IDX = list(range(30, 40))
if __name__ == "__main__":
    prior = WARM
    for i in IDX:
        tag = f"c{i:02d}"
        if not (OUT / f"{tag}.json").exists():
            m = C.run_one(dict(tag=tag, idx=i, prior=prior, variant=C.VAR, outdir=OUT, wdir="chain", save_prior=OUT / f"{tag}_end"))
            print(tag, m["label"], m.get("latched"), m.get("valid"), m.get("lock_latency_us"), m["reset_level"], m["ref_reset"], flush=True)
        prior = OUT / f"{tag}_end"
