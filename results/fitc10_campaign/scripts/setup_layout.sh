#!/bin/sh
# Recreate the /home/claude/w layout the design scripts hard-code, using symlinks only.
# Builds and runs happen in /home/claude/w/sim/circuits, which holds symlinks to rev10/sim/circuits,
# so generated netlists and outputs never land inside the repo's rev10/ tree.
set -e
R=$(cd "$(dirname "$0")/../../.." && pwd); W=/home/claude/w
mkdir -p $W/sim/circuits
ln -sfn "$R" $W/repo
ln -sfn "$R/rev10/eval" $W/eval
ln -sfn "$R/rev10/sim/models" $W/sim/models
ln -sfn "$R/rev10/sim/tools" $W/sim/tools
for f in "$R"/rev10/sim/circuits/*; do ln -sf "$f" $W/sim/circuits/; done
echo "layout ready under $W (repo $R)"
