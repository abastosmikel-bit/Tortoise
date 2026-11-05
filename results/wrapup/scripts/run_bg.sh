#!/bin/sh
# Background drivers of the wrap-up studies (all resumable; re-run this after a container restart, from a shell whose own
# command line does not contain the driver names, since pgrep -f matches command lines).
cd "$(dirname "$0")"
L=${WRAPUP_LOGS:-../logs}; mkdir -p $L
pgrep -f "s1_modew.py" >/dev/null || nohup sh run_s1.sh >> $L/s1b.log 2>&1 &
pgrep -f "s2_tail.sh" >/dev/null || nohup sh s2_tail.sh >> $L/s2chain.log 2>&1 &
pgrep -f "s3_runs.py K" >/dev/null || [ "$(ls ../raw/S3K/*.json 2>/dev/null | wc -l)" -ge 40 ] || nohup python3 s3_runs.py K 3 >> $L/s3K.log 2>&1 &
[ -f ../weights/FROZEN_S3.json ] || pgrep -f "s3_chain.py" >/dev/null || nohup python3 s3_chain.py >> $L/s3chain.log 2>&1 &
[ -f ../weights/FROZEN_S3.json ] && { pgrep -f "s3_eval_chain.sh" >/dev/null || nohup sh s3_eval_chain.sh >> $L/s3eval.log 2>&1 & }
