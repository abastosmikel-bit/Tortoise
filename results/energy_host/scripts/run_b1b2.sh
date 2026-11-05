#!/bin/bash
# Driver: B1 standby + options, then B2 1D. Logs in ../logs/. Resumable (every runner skips finished runs).
cd "$(dirname "$0")"; mkdir -p ../logs
while pgrep -f "b1_energy.py" >/dev/null; do sleep 20; done
echo "$(date +%T) B1 baseline done"
TAGS=$(python3 -c "
import json,glob
rs=[json.load(open(f)) for f in sorted(glob.glob('../raw/b1_energy/s*.json'))]
pick=[]
for k in range(1,6):
    c=[m['tag'] for m in rs if m.get('valid') and m.get('winner')==k]
    pick+=c[:1]
pick+=[m['tag'] for m in rs if not m.get('valid')][:1]
print(' '.join(pick))")
echo "standby tags: $TAGS"
python3 b1_standby.py $TAGS > ../logs/b1_standby.log 2>&1
echo "$(date +%T) standby done"
python3 b1_options.py chain > ../logs/b1_chain.log 2>&1 &
PC=$!
python3 -c "
import b1_options as O, eh
eh.pool_run(O.jobs('O2') + O.jobs('O12'), 3)" > ../logs/b1_O2_O12.log 2>&1
wait $PC
echo "$(date +%T) chain, O2, O12 done"
python3 b1_options.py O1 4 > ../logs/b1_O1.log 2>&1
echo "$(date +%T) O1 done"
python3 b2_retrim.py 1D 4 > ../logs/b2_1D.log 2>&1
echo "$(date +%T) B2 1D done"
