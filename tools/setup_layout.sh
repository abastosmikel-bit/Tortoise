#!/bin/sh
# Recreate the /home/claude/w layout that the design and campaign scripts hard-code, from a fresh clone, using
# symlinks only (the scripts' paths are not refactored). Same layout as results/fitc10_campaign/scripts/setup_layout.sh,
# which every campaign used; this copy lives at the top level so it does not depend on a campaign folder.
#
#   /home/claude/w/repo          -> <repo>                     (rev10 scripts read data/ through it)
#   /home/claude/w/eval          -> <repo>/rev10/eval
#   /home/claude/w/sim/models    -> <repo>/rev10/sim/models
#   /home/claude/w/sim/tools     -> <repo>/rev10/sim/tools
#   /home/claude/w/sim/circuits/ -> a real directory of symlinks to <repo>/rev10/sim/circuits/*
# Builds and simulations run in /home/claude/w/sim/<workdir>, so generated netlists never land inside the repo.
# Usage: sh tools/setup_layout.sh     (needs write access to /home/claude; re-running is safe)
set -e
R=$(cd "$(dirname "$0")/.." && pwd); W=/home/claude/w
mkdir -p $W/sim/circuits
ln -sfn "$R" $W/repo
ln -sfn "$R/rev10/eval" $W/eval
ln -sfn "$R/rev10/sim/models" $W/sim/models
ln -sfn "$R/rev10/sim/tools" $W/sim/tools
for f in "$R"/rev10/sim/circuits/*; do ln -sf "$f" $W/sim/circuits/; done
# prerequisites (reported, not installed)
command -v ngspice >/dev/null 2>&1 && ngspice --version 2>/dev/null | grep -o 'ngspice-[0-9a-z+.]*' | head -1 \
  || echo "WARNING: ngspice not found (apt-get install -y ngspice; ngspice-42 was used for every campaign)"
python3 -c "import numpy" 2>/dev/null || echo "WARNING: python3 numpy not found (pip install numpy)"
echo "layout ready under $W (repo $R)"
