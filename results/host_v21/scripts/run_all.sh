#!/bin/bash
# Driver (DECISIONS P3 order; resumable: every runner skips finished work). Log: logs/driver.log
cd "$(dirname "$0")"; L=../logs; log() { echo "$(date -u +%T) $1" >> $L/driver.log; }
log "start"
python3 phases21.py E1cal 4 > $L/E1cal.log 2>&1; log "E1cal done"
python3 phases21.py E1chain > $L/E1chain.log 2>&1 &
python3 phases21.py E1 4 > $L/E1.log 2>&1; log "E1 done"
python3 phases21.py E1forced 4 > $L/E1forced.log 2>&1; log "E1forced done"
python3 phases21.py E1idle 4 > $L/E1idle.log 2>&1; log "E1idle done"
wait; log "E1chain done"
python3 phases21.py nominal > $L/nominal.log 2>&1; log "nominal cal done"
python3 stress_ramp.py 1 > $L/E2_r1.log 2>&1; log "E2 1x done"
python3 stress_ramp.py 0.3 > $L/E2_r0p3.log 2>&1; log "E2 0.3x done"
python3 stress_ramp.py 3 > $L/E2_r3.log 2>&1; log "E2 3x done"
log "MAIN DONE"
