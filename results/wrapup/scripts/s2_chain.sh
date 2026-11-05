#!/bin/sh
# Study 2 driver (DECISIONS S2 with S2-D1/S2-D2): phase 1 (0.65, 0.49, 0.51 V) for both variants in parallel, then
# phase 2 (0.47, 0.45 V) for the better one, its 90-sample nominal run (S2-D1) and its stress audit. Resumable.
cd "$(dirname "$0")"
python3 s2_runs.py edge R10.2-edgeA 1 & a=$!
python3 s2_runs.py edge R10.2-edgeB 1 & b=$!
wait $a $b
python3 s2_runs.py edge2 x 2 || exit 1
best=$(python3 -c "import json; print(json.load(open('../summary/s2_phase2_choice.json'))['better'])")
python3 s2_runs.py nominal90 "$best" 2 && python3 s2_runs.py stress "$best" && python3 s2_summary.py
echo "S2 CHAIN DONE"
