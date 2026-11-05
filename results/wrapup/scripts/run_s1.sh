#!/bin/sh
# Study 1 driver (DECISIONS S1.7): calibrations, then classification runs, then the identity check.
cd "$(dirname "$0")"
python3 s1_modew.py cal 4 && python3 s1_modew.py runs 4 && python3 s1_modew.py check
