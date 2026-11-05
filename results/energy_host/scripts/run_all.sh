#!/bin/bash
# Campaign driver (resumable: every runner skips finished runs). Stops before B2 2D and B4 timing (declared later).
cd "$(dirname "$0")"; mkdir -p ../logs
commit() { echo "$(date +%T) checkpoint: $1"; }  # checkpoint marker (the original driver also committed the results here)
log() { echo "$(date +%T) $1"; }
log "driver (re)start"
python3 b1_standby.py s01 s04 s18 s07 s00 s24 > ../logs/b1_standby.log 2>&1
python3 b1_options.py chain > ../logs/b1_chain.log 2>&1
python3 -c "
import b1_options as O, eh
eh.pool_run(O.jobs('O2') + O.jobs('O12') + O.jobs('O1'), 4)" >> ../logs/b1_options.log 2>&1
log "B1 options done"
python3 b1_summary.py > ../logs/b1_summary.log 2>&1; commit "energy_host B1: host-only options O1, O2, O12"
for P in fixed formula rstb50 Vcal-200 Vcal-400 rext300; do python3 b5_edge.py short $P 4 > ../logs/b5_short_$P.log 2>&1; done
log "B5 short done"; commit "energy_host B5: short-run lower-edge thresholds per host policy"
python3 b3_mc.py offsets 4 > ../logs/b3_offsets.log 2>&1; python3 b3_mc.py est 4 > ../logs/b3_est.log 2>&1; log "B3 est done"
python3 b4_estimates.py 4 > ../logs/b4_est.log 2>&1; log "B4 est done"
commit "energy_host B3/B4: method offsets and estimates"
python3 b2_retrim.py 1D 4 > ../logs/b2_1D.log 2>&1; python3 b2_summary.py > ../logs/b2_summary.log 2>&1; log "B2 1D done"
commit "energy_host B2: 1D re-trim tolerance sweeps"
python3 b3_mc.py cls 4 > ../logs/b3_cls.log 2>&1; python3 b3_summary.py > ../logs/b3_summary.log 2>&1; python3 b3_best.py > ../logs/b3_best.log 2>&1
log "B3 cls done"; commit "energy_host B3: MC classification per method"
python3 b4_aging.py none 4 > ../logs/b4_none.log 2>&1; python3 b4_aging.py ideal 4 > ../logs/b4_ideal.log 2>&1
BEST=$(python3 -c "import json;print(json.load(open('../summary/b3_best.json'))['best'])")
python3 b4_aging.py $BEST 4 > ../logs/b4_$BEST.log 2>&1; log "B4 done ($BEST)"
commit "energy_host B4: aging map (none, ideal, $BEST)"
PB=$(python3 -c "
import json,glob
r={json.load(open(f))['policy']:json.load(open(f)) for f in glob.glob('../summary/b5_short_*.json')}
h={p:v['threshold_V']['lowest_working'] for p,v in r.items() if p not in ('fixed','formula') and 'threshold_V' in v}
print(min(h,key=h.get) if h else 'none')")
python3 b5_edge.py full fixed 4 > ../logs/b5_full_fixed.log 2>&1; python3 b5_edge.py full formula 4 > ../logs/b5_full_formula.log 2>&1
[ "$PB" != "none" ] && python3 b5_edge.py full $PB 4 > ../logs/b5_full_$PB.log 2>&1
log "B5 full done ($PB)"; commit "energy_host B5: full lower-edge runs (fixed, formula, $PB)"
log "DRIVER DONE (B2 2D and B4 timing need declarations E5/E9)"
