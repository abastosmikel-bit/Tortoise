#!/bin/bash
# Variant 3 campaign driver (D11): warm start -> Phase 1 (+chain) -> Phase 2 -> Phase 3, with commits. Log: ../driver_v3.log
cd "$(dirname "$0")"; export FC10_VARIANT=3
commit() { echo "$(date +%T) checkpoint: $1"; }  # checkpoint marker (the original driver also committed the results here)
echo "$(date +%T) start"
python3 warmstart.py > ../v3_warmstart.log 2>&1 || { echo "warmstart failed"; exit 1; }
commit "fitc10 Variant 3 Phase 0e: warm start"
python3 chain.py > ../v3_chain.log 2>&1 & PC=$!
python3 phase1.py 3 > ../v3_phase1.log 2>&1 & P1=$!
wait $P1; wait $PC
python3 summarize.py phase1; python3 summarize.py chain
commit "fitc10 Variant 3 Phase 1 complete: 90 runs + chain, summaries"
python3 phase2_audit.py 4 > ../v3_phase2.log 2>&1
commit "fitc10 Variant 3 Phase 2 stress audit"
python3 phase3.py AB 4 > ../v3_phase3.log 2>&1 & P3=$!
while kill -0 $P3 2>/dev/null; do
  for k in $(seq 120); do kill -0 $P3 2>/dev/null || break; sleep 10; done
  kill -0 $P3 2>/dev/null && commit "fitc10 Variant 3 Phase 3 checkpoint: $(ls ../raw/v3/phase3A/*.json 2>/dev/null | wc -l)/180 3A, $(ls ../raw/v3/phase3B/B_*s??.json 2>/dev/null | wc -l)/300 3B"
done
python3 summarize.py phase3A; python3 summarize.py phase3B
commit "fitc10 Variant 3 Phase 3 complete: corner sweeps and mismatch MC, summaries"
echo "$(date +%T) ALL DONE"
