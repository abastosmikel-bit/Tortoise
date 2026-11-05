#!/bin/sh
# Tortoise v1.0 smoke test: 5 real ngspice runs (lab #81; fitc10 Variant 3 #81 and #31; host v2.1 nominal and 0.51 V mode W,
# sample #1), each compared with its recorded outcome. See tools/smoke_test.py for the expected files and the match rule.
# Output: a table on stdout and $SMOKE_OUT/smoke_summary.json (default /tmp/tortoise_smoke); nothing inside the repo.
# Runtime: about 3 min on 4 cores (173 s measured in a fresh clone; see REPRODUCE.md §5).
set -e
R=$(cd "$(dirname "$0")/.." && pwd)
sh "$R/tools/setup_layout.sh"
s=$(date +%s)
PYTHONDONTWRITEBYTECODE=1 python3 "$R/tools/smoke_test.py" "$@"
echo "smoke_test.sh wall time: $(( $(date +%s) - s )) s"
