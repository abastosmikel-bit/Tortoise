#!/bin/sh
# Start a resumable script detached from the calling shell (survives a closed shell). Usage: launch_detached.sh <log> <args...>
LOG=$1; shift
cd "$(dirname "$0")"
setsid nohup python3 "$@" > "../$LOG" 2>&1 < /dev/null &
echo "started pid $! -> $LOG"
