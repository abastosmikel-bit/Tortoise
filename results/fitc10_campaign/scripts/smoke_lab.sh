#!/bin/sh
# Toolchain check at the LAB corner (lab_vth085), NOT fitc10: build #81 with the lab-corner builder's smoke-test
# command, simulate with RELAX=1, score it, and record wall time. Output: summary/smoke_lab_s81.json, raw/smoke81.log.gz
set -e
C=$(cd "$(dirname "$0")/.." && pwd); W=/home/claude/w/sim/circuits
sh "$C/scripts/setup_layout.sh"
cd $W
OUT=$W/smoke_s81.cir python3 ../tools/build_A.py 81 t6L_x2_v085
s=$(date +%s); RELAX=1 python3 ../tools/run_diag.py smoke_s81.cir smoke81 > /dev/null; e=$(( $(date +%s) - s ))
gzip -c _smoke81.log > "$C/raw/smoke81.log.gz"
python3 - "$e" "$C/summary/smoke_lab_s81.json" <<'PY'
import sys, json, re; sys.path.insert(0, '../tools'); from score import score
r = score('smoke81', t_on=320e-6, expect=5, t_off=5000e-6)
tran = re.search(r"^\.tran .*$", open('smoke_s81.cir').read(), re.M).group(0)
out = dict(corner="lab_vth085 (NOT fitc10)", sample_X_test_idx=81, prior="t6L_x2_v085", tran=tran,
           n_tft=sum(1 for l in open('smoke_s81.cir') if l.startswith('X')), wall_s=int(sys.argv[1]),
           trip_us=r['trip']*1e6 if r['trip'] else None, order=r['order'], latched=r['latched'],
           lock_us=r['lock']*1e6 if r['lock'] else None, lock_latency_us=r['lat'], valid=bool(r['valid']))
json.dump(out, open(sys.argv[2], 'w'), indent=1); print(out)
PY
