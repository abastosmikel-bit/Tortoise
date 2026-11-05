#!/bin/sh
# Study 2 tail (2026-10-31 02:45 UTC): same runs as s2_chain2.sh after the S2-D2 choice, run in parallel instead of in
# sequence: (a) phase 2 (0.47, 0.45 V) of the chosen variant; (b) after the running 90-sample nominal run, its stress
# audit. Then the summary.
cd "$(dirname "$0")"
python3 s2_runs.py edge2 x 2 & a=$!
while pgrep -f "s2_runs.py nominal90" >/dev/null; do sleep 30; done
python3 s2_runs.py nominal90 R10.2-edgeA 2 && python3 s2_runs.py stress R10.2-edgeA
wait $a
python3 s2_summary.py
echo "S2 CHAIN DONE"
