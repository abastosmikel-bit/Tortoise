# Tortoise host-v2.1 study: host protocol v2.1 (adaptive power gating + ramp-rate stress)

**Status: complete (2026-10-29 ≈ 21:30 UTC).** E1 (lower-edge sweep, 140 runs) with its forced-mode reference (20),
mode-W chain (20) and standby idles (160); E2 (ramp-rate stress, 3 rates + the pre-declared 2-rate extension, 25 audited
runs). No post-freeze deviations (DECISIONS P4).
Circuit frozen: Variant 3 at `fitc10`, weights `rev10/eval/F_hw_m4_firstpass.npy`; **only the host protocol changes.**
Protocol v2.1 was frozen in [DECISIONS.md](DECISIONS.md) P2/P3 (commit `1db5914`) before any evaluation run; the only
earlier runs were a tooling check that reproduces an existing v2 run and the design-time mode-W run on the nominal die
(P1). Every number below is recomputed from per-run JSONs by `scripts/summ21.py` (tables in
[summary/e1_tables.md](summary/e1_tables.md), [summary/e2_tables.md](summary/e2_tables.md)). Nothing here is verified or
validated; this is simulation of a reconstructed model.

## 1. Summary
<!-- SUMMARY -->
- **E1 lower edge under v2.1 (7 points × N = 20, µ ×1):** **15/20 at every point from 0.51 to 0.61 V** (Wilson 95 %
  53–89 %), validity 20/20, and per-sample outcomes **identical to the v2 nominal cell (0.65 V) on 20/20 at each
  point**. v2 at the same points: 0/20 at 0.51–0.57 V, 15/20 at 0.59 and 0.61 V. Pooled N = 140: v2.1 90/140 vs v2
  30/140; paired 60 v2.1-only, 0 v2-only (exact McNemar p = 1.7·10⁻¹⁸).
- **0.49 V still fails under v2.1: 0/20 (FAILURE)** (16 `timeout`, 4 `none_latched`; calibration flagged). The lower
  edge moves from 0.57–0.59 V (v2) to **between 0.49 and 0.51 V** (bracketed by two 20-sample points, not bisected).
  The failure at 0.49 V is not the v2 stuck latch: the latches reset, but the comparator/latch swing is too weak to
  regenerate.
- **Modes (N = 140 + 20):** all 20 runs of each point ended in the mode its calibration chose: **W at 0.49–0.59 V
  (120 runs), G at 0.61 V (20 runs)**, as predicted before the freeze. Near the threshold (0.600 V) the estimates were
  0.5940 V (true 0.59, → W) and 0.6064 V (true 0.61, → G). **Both modes give the same 20 outcomes at both points**
  (0.59 V: v2.1-W vs v2-G 20/20; 0.61 V: forced W vs v2.1-G 20/20), so a wrong mode choice near the threshold cost no
  accuracy here; it costs standby.
- **Standby paid by the VDD-on dies (N = 120 idles + 20 forced):** **174–209 µW** (mean over the 1 s idle; rises as
  |V_th| falls: 0.59 V 174 µW, 0.51 V 192 µW, 0.49 V 209 µW; 169 µW at 0.61 V forced W), i.e. **≈ 174–210 µJ per
  classification at 1 classification/s**, against **0.65 µJ** (646 nJ, standby 0) for the gated die at 0.61 V: ≈ 270–320×
  more. The classification itself is cheaper in mode W (395–468 nJ at 0.51–0.59 V, warm start, shorter race).
- **Mode-W history (chain at 0.51 V, N = 20):** 14/19 valid vs 15/20 independent; **19/20 outcomes identical**; the one
  change is near-tie #31 (class 2 → double latch). Races 5.7–19.0 µs longer than the independent runs (v2 gated chain:
  ≤ 0.003 µs; v1 warm chain: ≤ 4.1 µs).
- **E2 ramp-rate stress (5 runs × 134 TFTs per rate, both power-up and power-down):** **0 TFTs above 3.5 V at 0.3×, 1×
  and 3× the C2 rate**, and also at the declared extension 0.1× and 10×. Worst device 3.330 V (0.3×, X84), 3.300 V (1×,
  = v2 C2 exactly), 3.374 V (3×, XWR |V_GD|), 3.436 V (10×, XWR, margin 0.064 V). Crossbar peak 3.01–3.05 V. Most
  negative internal node −2.04…−2.06 V at power-up (start state) and **−2.20…−2.21 V at power-down at every rate**.
  **Tested range that stays below 3.5 V: 0.1×–10× (ramp 100 µs … 1 µs, 0.033–3.3 V/µs); limits outside it not tested.**
<!-- /SUMMARY -->

## 2. Host protocol v2.1 (frozen definition: DECISIONS P2)
v2.1 = v2 (host_v2 DECISIONS H2 + H4) **plus adaptive power gating.** After its a1 calibration (unchanged: cold power-up,
supply-current transfer, V̂ = V_raw − c_a1) the host picks one mode for the die:

| | **Mode G** (V̂ ≥ 0.600 V) = v2 | **Mode W** (V̂ < 0.600 V) |
|---|---|---|
| Between classifications | VDD and all lines 0 V for 1 s | **VDD on**, lines at idle levels, 1 s |
| Start of a classification | power-up ramp from the 1 s-off state | warm (state the idle leaves) |
| `rstr` | 0 V from t = 0 (cold) | 3.3 → 0 V over 0–20 µs (v1) |
| `rstb` release | 50 µs | **50 µs (the energy/host study's v1 fix, E11.1)** |
| Levels, k, T₁, reset extension, early end (integrating timer), timeout | v2 | v2 |
| Race cross-check offset | c_race = −34.48 mV | **c_race,W = −8.05 mV** (nominal die run through the mode-W sequence) |
| Standby | 0 | paid (P2.4) |

The host uses only its line levels and timer, the five outputs, and the I_DD meter; the mode decision uses only V̂.

**Threshold from the v2 C6 data (DECISIONS P2.0).** v2 classified at the nominal rate from 0.59 V (15/20, with a 13 µs
pre-trip timer count out of D = 50 µs) and failed at 0.57 V (0/20). The a1 error over all 39 v2 calibrations was
−4.4…+8.5 mV. V_gate = 0.59 V + 8.5 mV, rounded up: **0.600 V**. A die then runs v2 only if its true |V_th| ≥ 0.5915 V
(with v2-sized errors); dies up to ≈ 0.604 V may run mode W, so W was also tested just above the threshold (0.61 V forced).

## 3. E1: the lower edge (140 runs + 20 forced + 20 chain)
Sources: [e1_lower_edge.json](summary/e1_lower_edge.json), per run [e1_runs.csv](summary/e1_runs.csv), runs `raw/E1/`,
`raw/E1forced/`, `raw/E1chain/`, calibrations `raw/cal/`. µ ×1, global corner, no mismatch, the 20-sample subset, each
point its own calibration session; independent runs from the calibration start state.

**v2 vs v2.1** (correct / valid of 20; v2 = host_v2 C6/C6b runs, imported).

| \|V_th\| (V) | V̂ (err mV), flag | v2.1 mode | **v2.1** | v2 | paired both / v2.1 only / v2 only / neither (exact McNemar p) | v2.1 median race (µs) | v2 median race (µs) |
|---|---|---|---|---|---|---|---|
| 0.49 | 0.4936 (+3.6), **flag** (races time out) | W | **0 / 0** (timeout 16, none_latched 4) | 0 / 0 (stuck_latched 20) | 0 / 0 / 0 / 20 (1) | 1545 (4 runs that trip) | — |
| 0.51 | 0.5131 (+3.0) | W | **15 / 20** | 0 / 0 (stuck_latched 20) | 0 / 15 / 0 / 5 (6·10⁻⁵) | 1330 | — |
| 0.53 | 0.5325 (+2.5) | W | **15 / 20** | 0 / 0 (stuck_latched 20) | 0 / 15 / 0 / 5 (6·10⁻⁵) | 1295 | — |
| 0.55 | 0.5518 (+1.8) | W | **15 / 20** | 0 / 0 (stuck_latched 20) | 0 / 15 / 0 / 5 (6·10⁻⁵) | 1269 | — |
| 0.57 | 0.5719 (+1.9) | W | **15 / 20** | 0 / 0 (none_latched 20) | 0 / 15 / 0 / 5 (6·10⁻⁵) | 1231 | 1678 |
| 0.59 | 0.5940 (+4.0) | W | **15 / 20** | 15 / 20 | 15 / 0 / 0 / 5 (1) | 1171 | 1656 |
| 0.61 | 0.6064 (−3.6) | G | **15 / 20** | 15 / 20 | 15 / 0 / 0 / 5 (1) | 1754 | 1754 |
| **pooled (140)** | | | **90 / 120** | 30 / 40 | 30 / 60 / 0 / 50 (1.7·10⁻¹⁸) | | |

- **Every working point reproduces the nominal die:** at 0.51–0.61 V the 20 per-sample outcomes are identical to the
  v2 C3 nominal cell (0.65 V, µ ×1) at every point, and the 5 failures are the same near-tie samples.
- **0.61 V (mode G) reproduces v2 C6b exactly** (20/20 outcomes and race times), as mode G is v2 by definition.
- **No pre-trip timer counts in mode W** (0 µs on every run that tripped; v2 counted 2–27 µs at 0.57–0.61 V): with VDD
  on, `na` has decayed well below 1.65 V when counting starts (highest losing `na` at the read 0.83–1.12 V, median).
- **Calibration in mode W:** the race cross-check agrees with a1 within +0.2…+6.0 mV at 0.51–0.59 V (no flags; v2
  flagged every point 0.45–0.55 V because no race finished). At 0.49 V both x = 0 races time out (flag).

**Which mode each run ended in.** All 20 runs of each point ran in its calibration's mode (W: 0.49–0.59 V, 120 runs;
G: 0.61 V, 20 runs). The mode is decided once per calibration session, so a die never mixes modes between
classifications. Near the threshold:

| Point | V̂ | Distance to V_gate | Mode | Other mode on the same die | Outcomes, the two modes |
|---|---|---|---|---|---|
| 0.59 V | 0.5940 V | −6.0 mV | W (15/20) | G = v2 C6b (15/20) | 20/20 identical |
| 0.61 V | 0.6064 V | +6.4 mV | G (15/20) | **W forced** (15/20, standby 169 µW) | 20/20 identical |

So within ±6 mV of the threshold either mode classifies at the nominal rate on these samples. The threshold sets the
standby cost, not the accuracy, in this range. Mode G at 0.59 V works with a 13 µs pre-trip count (thin; v2 failed at
0.57 V), which is why the threshold sits above it.

**Why 0.49 V still fails (post-hoc, waveforms of sample #1 at 0.49/0.51/0.53 V; analysis, not a protocol test).**
Mode W fixes the v2 stuck latch: at 0.49 V `na` decays to 1.19 V by 320 µs (v2: stuck at 3.2 V). But `ref` samples to
≈ 1.65 V, the rails must climb to ≈ 2.64 V before `na` reaches 1.65 V (2.37 V at 0.51 V), and the comparator output `d`
falls only to 2.82 V (2.67 V at 0.51 V; `vls` ≈ 3.0 V). The trip driver X83 then pushes `na` only just past 1.65 V
(1.66 V at the read on #1) or not at all within 4000 µs (16/20 `timeout`), and the latch does not regenerate. This is the
weak-latch region the energy/host study reported at 0.48–0.52 V (13/17 at 0.50 V, 3 hovering outputs), now crossing below 0.51 V.

**Mode-W history (P3.3, chain at 0.51 V).**

| | correct / valid | same outcome as independent | race shift vs independent |
|---|---|---|---|
| Independent (E1, from the calibration start state) | 15 / 20 | — | — |
| **Chain** (subset order, 1 s VDD-on idle between) | 14 / 19 | 19 / 20 (#31: class 2 → `multi_latched`) | +5.7 … +19.0 µs (steps 1–19) |

- The independent runs all start from the state after the x = 0 calibration race, in which **all five latches are
  high** (that race double-latches everywhere). In the chain each step starts with one latch high, `ref` samples 7.7–9.8 mV
  higher and the race is 6–19 µs longer; the rail reset level is unchanged (0.7487 vs 0.7489 V). So mode W brings back a
  history channel that v2's gating had removed (v2 chain ≤ 0.003 µs, v1 chain ≤ 4.1 µs). It changed one near-tie
  sample here. The chain is the more representative mode-W operation; the independent-run start state is atypical
  (disclosed after the fact; not a protocol change).

## 4. Energy and standby (P2.4; all runs, source currents)
| \|V_th\| (V) | Mode | Energy per classification, median (range) | Standby mean over 1 s, median (range) | At 1 ms / 1 s | Per classification at 1 /s |
|---|---|---|---|---|---|
| 0.49 | W | 1070 nJ (497–1070; mostly 4000 µs timeouts) | 209.2 µW (209.2–209.2) | 210.9 / 207.5 µW | ≈ 210 µJ |
| 0.51 | W | 468 nJ (386–524) | 192.1 µW (192.1–192.2) | 193.2 / 191.1 µW | ≈ 193 µJ |
| 0.53 | W | 450 nJ (370–505) | 187.7 µW | 188.3 / 187.0 µW | ≈ 188 µJ |
| 0.55 | W | 434 nJ (356–489) | 183.1 µW | 183.4 / 182.7 µW | ≈ 184 µJ |
| 0.57 | W | 417 nJ (340–470) | 178.4 µW | 178.6 / 178.2 µW | ≈ 179 µJ |
| 0.59 | W | 395 nJ (322–447) | 173.7 µW | 173.7 / 173.6 µW | ≈ 174 µJ |
| 0.61 | G | 646 nJ (548–714) | 0 (power-down energy not credited) | 0 / 0 | **0.65 µJ** |
| 0.61 forced W | W | 394 nJ | 169.1 µW | — | ≈ 169 µJ |

- Standby barely moves within the 1 s (< 2 %) and hardly depends on which class won (range < 0.1 µW per point); it is
  the static current of the level-shift bias and the ratioed latch loads (energy/host study §2.5: 199 µW just after a
  classification, relaxing to 98 µW only after ≈ 10³ s).
- **At 1 /s the VDD-on die spends ≈ 270–320× the energy of a gated die.** Mode W is cheap only when the idle is short (e.g. a
  0.2 ms idle after a ≈ 1.8 ms classification would cost ≈ 36 nJ at ≈ 180 µW); not evaluated here.
- Not counted (as v2): host electronics, the I_DD meter, energy returned at power-down.

## 5. E2: ramp-rate stress (P3.5; 5 runs per rate, 134 TFTs)
Sources: [e2_ramp.json](summary/e2_ramp.json), per device [e2_devices.csv](summary/e2_devices.csv), runs `raw/E2/`;
script `scripts/stress_ramp.py` (uses `host_v2/scripts/stress.py`'s audit, read-only). Same runs as v2 C2 (maxsum #17,
minsum #61, maxcol #29, mincol #1, #31 after #30 with a power-down + 1 s off), nominal die (mode G under v2.1). The rate
scales the power-up (VDD, rows, `phi`: 0 → level) and the power-down (every source → 0 V); stress = max(|V_GS|, |V_GD|).

| Rate (× C2) | Ramp / slope | Segment | TFTs > 3.5 V | Worst TFT: max \|V_GS\| / \|V_GD\| (V), time | Margin | Crossbar peak | Most negative internal node |
|---|---|---|---|---|---|---|---|
| 0.1× (ext.) | 100 µs / 0.033 V/µs | up | 0 | XWR 3.300 / 3.118, 100 µs | 0.200 V | 3.009 V (X1) | −2.062 V (`nb1`, start state) |
| | | down | 0 | X69 2.119 / 3.300, 0 µs | 0.200 V | 1.653 V | −2.214 V (`nb1`, 102 µs) |
| **0.3×** | 33.3 µs / 0.099 V/µs | up | **0** | **X84 3.330 / 0.000, 50.9 µs** | 0.170 V | **3.021 V** (X1) | **−2.048 V** (`nb1`, start state) |
| | | down | **0** | X69 2.119 / 3.300, 0 µs | 0.200 V | 1.891 V | **−2.201 V** (`nb1`, 35 µs) |
| **1×** (C2) | 10 µs / 0.33 V/µs | up | **0** | **XNP1 3.300 / 3.286, 10 µs** | 0.200 V | **3.033 V** (X1) | **−2.042 V** (`nb1`, start state) |
| | | down | **0** | X69 2.120 / 3.300, 0 µs | 0.200 V | 2.021 V | **−2.197 V** (`nb1`, 15 µs) |
| **3×** | 3.33 µs / 0.99 V/µs | up | **0** | **XWR 3.300 / 3.374, 3.7 µs** | 0.126 V | **3.041 V** (X13) | **−2.040 V** (`nb1`, start state) |
| | | down | **0** | X69 2.120 / 3.300, 0 µs | 0.200 V | 2.078 V | **−2.196 V** (`nb1`, 7 µs) |
| 10× (ext.) | 1 µs / 3.3 V/µs | up | 0 | XWR 3.300 / 3.436, 1.3 µs | **0.064 V** | 3.048 V (X8) | −2.039 V (`nb1`, start state) |
| | | down | 0 | X69 2.120 / 3.300, 0 µs | 0.200 V | 2.111 V | −2.195 V (`nb1`, 6 µs) |

- **The 1× runs reproduce v2 C2 exactly** (every device's max stress to 0.000 V, same lowest nodes, same outcomes).
  At every rate all 5 classifications give the same outcome as at 1× (race shift ≤ 0.4 µs).
- **Range below 3.5 V: every tested rate, 0.1×–10× (ramp 100 µs to 1 µs).** The main grid (0.3×, 1×, 3×) passed, so the
  pre-declared extension (0.1×, 10×) was run; it also passed. Faster than 10× and slower than 0.1× were not tested.
- **Fast ramps cost margin through overshoot, not DC levels.** At 3× and 10× the `win` node (0.3 pF, precharged by XWR from
  `rstr`) overshoots above VDD right after the ramp (3.374 / 3.436 V), stressing XWR's gate–drain and X80. The trend
  3.300 → 3.374 → 3.436 V (1×/3×/10×) suggests the limit lies not far above 10×; this is a trend, not a result.
- **Slow ramps:** at 0.3× the latch nodes `na1–5` overshoot VDD by 30 mV when `rstb` releases at 51 µs (X84 family
  3.330 V); at 0.1× the 100 µs power-up ramp is still running when `rstb` releases at 50 µs (the protocol timing was not
  scaled with the ramp, P3.5) and the worst device is 3.300 V.
- **Crossbar:** 3.01–3.05 V at the end of the power-up ramp at every rate (rows at 3.3 V against rails near 0.25 V);
  margin 0.45–0.49 V.
- **Negative nodes do not depend on the ramp rate:** the power-down drives `nb1` (and the other latch nodes) to
  −2.20…−2.21 V at every rate from 100 µs to 1 µs, and the next power-up starts from ≈ −2.04…−2.06 V. A slower uniform
  power-down (v2 proposal 5) does not remove them; sequencing the lines (not tried) would be the remaining option.

## 6. v2 vs v2.1
| Condition (N) | v2 | **v2.1** | Source |
|---|---|---|---|
| Lower edge, 0.49–0.61 V (7 × 20) | 30/140; works from 0.59 V; fails at 0.57 V | **90/140; works from 0.51 V; fails at 0.49 V** | E1 |
| 0.51–0.57 V (4 × 20) | 0/80 (stuck or `none_latched`) | **60/80, outcomes = nominal cell** | E1 |
| 0.59 / 0.61 V (2 × 20) | 15 / 15 | 15 / 15 (identical outcomes) | E1 |
| Standby, dies with V̂ < 0.600 V | 0 | **174–209 µW** (≈ 0.17–0.21 mJ per classification at 1 /s) | E1 idles |
| Standby, dies with V̂ ≥ 0.600 V | 0 | 0 | E1 |
| History (chain, 20) | ≤ 0.003 µs race shift, 0 changes (0.65 V) | mode W at 0.51 V: +5.7…+19 µs, 1 change (near tie) | E1chain / C1 |
| Ramp stress, 1× (5 runs) | 0/134 > 3.5 V, worst 3.30 V | identical (mode G = v2) | E2 |
| Ramp stress, 0.1×–10× | not tested | 0/134 > 3.5 V at every rate; worst 3.436 V (10×) | E2 |

## 7. What this does not show
- **Not measured hardware.** Simulation only; `fitc10` is a reconstructed corner (C10-DNTT on Si, currents read by eye);
  JOFF and LOV are not fitted; the Variant 3 sizing is rebuilt from the author's decisions. Standby is static current through
  compact-model devices whose subthreshold and leakage behaviour is the least certain part of the model.
- **The host is ideal:** noise-free I_DD meter and timer, ideal line drivers and ramps, 1 mV level resolution. A noisy
  a1 estimate near 0.600 V would only change the mode (§3 shows both modes work within ±6 mV of the threshold); the
  threshold has no hysteresis and re-calibration policy is not studied.
- **Lower edge:** 20 samples per point, µ ×1, no mismatch, global corners only. The v2.1 edge lies between 0.49 and
  0.51 V; it was not bisected. The 0.49 V mechanism comes from waveforms of one sample. Mode W at low |V_th| combined
  with µ loss, mismatch or aging was not run.
- **Mode W's history:** one 20-step chain at one point (0.51 V). The independent runs start from an atypical state
  (all latches high after the x = 0 calibration race). Longer chains, other points and other idle lengths were not run.
- **Standby:** the idle is exactly 1 s, VDD 3.3 V; longer idles relax toward ≈ 98 µW (energy/host study), shorter ones were not
  simulated. Host electronics and the meter are not counted.
- **Threshold:** derived from v2's 20-sample points and the v2 a1 error range (which was itself measured on 39 noise-free
  calibrations); a die between 0.57 and 0.59 V with an estimate error larger than +8.5 mV could run v2 where v2 fails.
- **Ramp stress:** nominal die only, 5 input picks, mode G; the ramp is linear and common to VDD, rows and `phi`
  (power-up) and to every source (power-down); protocol timing (e.g. `rstb` release) is not scaled with the ramp. The
  start state at each rate comes from one power-down after the calibration's race b (the calibration itself was not
  repeated per rate). Aged, low-|V_th| or mismatched dies, mode W (which has no power cycling per classification),
  sequenced supplies and ringing from real supply impedance were not audited. The limits beyond 0.1× and 10× are unknown.
- **Weights:** results apply to `F_hw_m4_firstpass.npy` only. N = 20 per point: one sample is 5 points.

## 8. Proposals (separate from the results; none simulated)
1. **Lower edge below 0.51 V needs a circuit change** (energy/host study §8 item 5): drive `d` to VDD when idle or strengthen the
   trip/regeneration path; the 0.49 V failure is a weak comparator/latch swing, which no host timing tested here fixes.
2. **Use the calibration's own outcome for the mode choice:** the x = 0 races already show whether a die latches under v2;
   a host could pick mode G when both races finish and mode W only when they do not, instead of a fixed V̂ threshold.
3. **Cheaper mode W:** standby (≈ 190 µW) dominates; options are a shorter idle with VDD on only for bursts, or a
   power-gated mode with a host-side `ref` precharge line (the v2 mechanism was the lost `ref` charge). Needs a circuit
   or pin change for the latter.
4. **Start mode-W classifications from a representative state:** end the calibration with one ordinary-input dummy
   classification so the first real run does not start with all latches high.
5. **Supply sequencing** to address the −2.2 V nodes (rate alone does not); and a ramp limit of ≲ 10× (1 µs) with margin
   for `win` overshoot, to be confirmed with supply impedance in the model.

## 9. Reproduce
```
sh results/fitc10_campaign/scripts/setup_layout.sh      # /home/claude/w layout (symlinks)
cd results/host_v21/scripts
python3 phases21.py E1cal 4 && python3 phases21.py E1 4 && python3 phases21.py E1chain
python3 phases21.py E1forced 4 && python3 phases21.py E1idle 4
python3 phases21.py nominal && python3 stress_ramp.py 1 0.3 3 && python3 stress_ramp.py 10 0.1
python3 summ21.py all
```
Runs are cached: each script skips work whose JSON exists. ngspice-42.
