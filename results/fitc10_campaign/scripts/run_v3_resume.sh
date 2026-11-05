#!/bin/bash
# Resume Variant 3 Phase 3 after the container restart at ~15:58 UTC (phase3.py skips runs whose json exists),
# then summarize and commit. Log: ../driver_v3_resume.log
cd "$(dirname "$0")"; export FC10_VARIANT=3
commit() { echo "$(date +%T) checkpoint: $1"; }  # checkpoint marker (the original driver also committed the results here)
sh setup_layout.sh
echo "$(date +%T) resume"
python3 phase3.py AB 4 >> ../v3_phase3.log 2>&1 & P3=$!
while kill -0 $P3 2>/dev/null; do
  for k in $(seq 120); do kill -0 $P3 2>/dev/null || break; sleep 10; done
  kill -0 $P3 2>/dev/null && commit "fitc10 Variant 3 Phase 3 checkpoint: $(ls ../raw/v3/phase3B/B_*s??.json 2>/dev/null | wc -l)/300 3B"
done
python3 summarize.py phase3A; python3 summarize.py phase3B
commit "fitc10 Variant 3 Phase 3 complete: corner sweeps and mismatch MC, summaries"
echo "$(date +%T) ALL DONE"
