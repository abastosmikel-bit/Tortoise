#!/bin/bash
# E11 follow-ups. Resumable. Summaries after each item.
cd "$(dirname "$0")"; log() { echo "$(date +%T) $1"; }
log "E11 start"
python3 -c "
import b5_edge as B, eh
js=[j for j in B.full_jobs('rstb50') if any(f'_v{v}_' in j['tag'] for v in ('0650','0500'))]
js+=[j for j in B.full_jobs('fixed') if '_v0550_' in j['tag']]
eh.pool_run(js, 4)" > ../logs/e11_b5.log 2>&1
python3 b5_summary.py > ../logs/b5_summary.log 2>&1; log "E11.1 B5 done"
python3 -c "
import b4_aging as A, eh
js=[A.job(0.65, 0.5, 1.82, 2.4, i, 'timing_x2', T1=340.0, trace=5000.0) for i in eh.SUB]
eh.pool_run(js, 4)" > ../logs/e11_b4t.log 2>&1; log "E11.2 B4 timing done"
python3 -c "
import b3_mc as B, eh
keep=('an20_d03','an20_d01','an35_d10','an35_d09')
eh.pool_run([j for j in B.cls_jobs() if j['die_key'] in keep], 4)" > ../logs/e11_b3.log 2>&1
python3 b3_summary.py > ../logs/b3_summary.log 2>&1; log "E11.3 B3 done"
log "E11 DONE"
