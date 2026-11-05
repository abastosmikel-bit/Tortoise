"""B1.1-1.3: energy per classification on all 90 test samples, baseline protocol (Variant 3, fitc10, warm start,
2500 us window), instrumented (DECISIONS E1). Resumable.  -> raw/b1_energy/s<idx>.{json,csv.gz,cir.gz}"""
import sys
import eh

if __name__ == "__main__":
    nproc = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    out = eh.RAW / "b1_energy"
    eh.pool_run([dict(tag=f"s{i:02d}", idx=i, outdir=out, wdir="b1", save_end=True) for i in range(90)], nproc)
