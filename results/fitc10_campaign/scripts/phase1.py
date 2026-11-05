"""Phase 1: all 90 test samples, Variant 1, fitc10 warm start (raw/warmstart/fitc10_warm), 2500 us window.
Independent runs in parallel (one ngspice per process). Resumable: skips samples whose json exists.
Usage: python3 phase1.py [nproc]   -> raw/phase1/s<idx>.{json,csv.gz,cir.gz}"""
import sys, json, time
from multiprocessing import Pool
import common as C

WARM = C.RAW / "warmstart/fitc10_warm"
OUT = C.RAW / "phase1"
if __name__ == "__main__":
    nproc = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    jobs = [dict(tag=f"s{i:02d}", idx=i, prior=WARM, variant=C.VAR, outdir=OUT, wdir="p1")
            for i in range(90) if not (OUT / f"s{i:02d}.json").exists()]
    s = time.time()
    with Pool(nproc) as p:
        for k, m in enumerate(p.imap_unordered(C.run_one, jobs), 1):
            print(f"[{k}/{len(jobs)} {time.time()-s:6.0f}s] {m['tag']} label {m['label']} latched {m.get('latched')} "
                  f"valid {m.get('valid')} {m.get('failure')} lat {m.get('lock_latency_us')} wall {m['run']['wall_s']}", flush=True)
