#!/bin/sh
# Study 2 driver, order revised 2026-10-30 21:40 UTC (same runs as s2_chain.sh): phase 1 (0.65, 0.49, 0.51 V) for both
# variants; the S2-D2 choice; then the chosen variant's 90-sample nominal run (S2-D1) and stress audit; then its
# phase 2 (0.47, 0.45 V). Resumable; waits for phase-1 drivers already running.
cd "$(dirname "$0")"
while pgrep -f "s2_runs.py edge R10.2" >/dev/null; do sleep 30; done
python3 s2_runs.py edge R10.2-edgeA 1 & a=$!
python3 s2_runs.py edge R10.2-edgeB 1 & b=$!
wait $a $b
python3 s2_runs.py edge2 x --choose-only || exit 1
best=$(python3 -c "import json; print(json.load(open('../summary/s2_phase2_choice.json'))['better'])")
python3 s2_runs.py nominal90 "$best" 2 && python3 s2_runs.py stress "$best"
python3 s2_runs.py edge2 x 2 && python3 s2_summary.py
echo "S2 CHAIN DONE"
