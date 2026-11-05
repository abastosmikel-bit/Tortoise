#!/bin/bash
# Driver for the rest of the campaign: finish Phase 1 -> summarize -> wait for Phase 2 -> Phase 3 (Variant 1, D9),
# with checkpoint commits. Logs to ../driver.log
cd "$(dirname "$0")"
commit() { echo "$(date +%T) checkpoint: $1"; }  # checkpoint marker (the original driver also committed the results here)
while pgrep -f "phase1.py" >/dev/null; do sleep 30; done
python3 summarize.py phase1; python3 summarize.py chain
commit "fitc10 Phase 1 (Variant 1) complete: 90 runs + 10-run chain, summaries"
while pgrep -f "phase2_audit.py" >/dev/null; do sleep 30; done
commit "fitc10 Phase 2 (Variant 1) stress audit"
python3 phase3.py AB 4 > ../phase3.log 2>&1 &
P=$!
while kill -0 $P 2>/dev/null; do sleep 1200; commit "fitc10 Phase 3 checkpoint: $(ls ../raw/phase3A/*.json 2>/dev/null | wc -l)/180 3A, $(ls ../raw/phase3B/B_*s??.json 2>/dev/null | wc -l)/300 3B"; done
python3 summarize.py phase3A; python3 summarize.py phase3B
commit "fitc10 Phase 3 (Variant 1) complete: corner sweeps and mismatch MC, summaries"
echo "$(date +%T) ALL DONE"
