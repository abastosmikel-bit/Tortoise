#!/bin/bash
# Driver after the E10 scope cut: B2 1D (50 mV) -> B4 3x3 (none, ideal). Resumable. Summaries after each phase.
cd "$(dirname "$0")"; log() { echo "$(date +%T) $1"; }
log "final driver start"
python3 b2_retrim.py 1D50 4 > ../logs/b2_1D50.log 2>&1; python3 b2_summary.py > ../logs/b2_summary.log 2>&1; log "B2 1D50 done"
python3 b4_aging.py none --3x3 > ../logs/b4_none.log 2>&1; python3 b4_aging.py ideal --3x3 > ../logs/b4_ideal.log 2>&1
python3 b4_summary.py > ../logs/b4_summary.log 2>&1; log "B4 3x3 done"
log "FINAL DRIVER DONE"
