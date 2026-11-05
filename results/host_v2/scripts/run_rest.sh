#!/bin/bash
# Driver after C1 (resumable: every runner skips finished work). Log: logs/driver.log
cd "$(dirname "$0")"; L=../logs; log() { echo "$(date -u +%T) $1" >> $L/driver.log; }
python3 stress.py > $L/C2.log 2>&1; log "C2 done"
while pgrep -f "phases.py C1" > /dev/null; do sleep 30; done
log "C1 chain done"; python3 summ_phases.py C1 > $L/summ_C1.log 2>&1
python3 phases.py C3cal 4 > $L/C3cal.log 2>&1; log "C3cal done"
python3 phases.py C5 > $L/C5.log 2>&1 &
python3 phases.py C3 3 > $L/C3.log 2>&1; log "C3 done"
python3 summ_phases.py C3 > $L/summ_C3.log 2>&1
python3 phases.py C3ideal 3 > $L/C3ideal.log 2>&1; log "C3ideal done"
python3 phases.py C4 3 > $L/C4.log 2>&1; log "C4 done"
wait; log "C5 done"
python3 phases.py C6 4 > $L/C6.log 2>&1; log "C6 done"
python3 summ_phases.py all > $L/summ_all.log 2>&1; log "ALL DONE"
