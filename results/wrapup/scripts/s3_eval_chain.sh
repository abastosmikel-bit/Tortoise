#!/bin/sh
# Study 3 evaluation of the single frozen choice (DECISIONS S3.4 with S3-D2): test set once (90), stress audit, then
# mismatch on 3 paired dies. s3_runs.py refuses to run unless the weights match FROZEN_S3.json and are committed.
cd "$(dirname "$0")"
python3 s3_runs.py test 3 && python3 s3_runs.py stress && python3 s3_runs.py mm 3 && python3 s3_summary.py eval
echo "S3 EVAL DONE"
