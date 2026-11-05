# Tortoise energy/host study: energy, host re-trim and aging (Variant 3 at `fitc10`)

**Status: final (2026-10-27 14:30 UTC) within the scope cut E10, plus the E11 follow-ups.** Scope cut by the author on 2026-10-27 (DECISIONS E10):
B4 reduced to a 3 × 3 grid without method re-trim, B2 to 1D sweeps at 50 mV steps, B3 classification runs and B5 full
runs only if time remains. 
Circuit: Variant 3 at `fitc10` (fitc10 campaign D9/D11), weights `rev10/eval/F_hw_m4_firstpass.npy` (**all results apply
to these weights**; the weight-retraining study was retraining them in parallel). Decisions: [DECISIONS.md](DECISIONS.md).
Every number is recomputed from per-run JSONs by the committed `scripts/*_summary.py`.
Aging inputs are **literature proxies**, not measurements of this process. Nothing here is verified or validated.

## 1. Summary
- **Energy per classification (B1, N = 90):** median **714 nJ** (684–717 nJ) with the 2500 µs race window; 99.97 % from
  VDD; host lines ≈ 0.3 nJ net (≈ 7 nJ in a 3.3 V driver model). Consumers: level-shift bias X65/X66 358 nJ, latch and
  lock loads 250 nJ, crossbar 85 nJ. Energy up to the lock = 169 nJ + 0.215 nJ/µs × race time (r = 0.998; 275–416 nJ).
- **Standby (B1, 6 end states):** 199 µW just after a classification, **98.2 µW** steady (after ≈ 10³ s); 87.5 µW with
  two latches set. With VDD on, idle dominates: ≈ 198 µJ per classification at 1 classification/s.
- **Host-only energy options (B1, N = 90 each, declared E3):** adaptive race end (O1) **372 nJ (290–433), −48 %**,
  accuracy 62/90 unchanged (1 outcome change, an already-wrong sample); VDD power-gated idle with cold start (O2)
  829 nJ, 90/90 outcomes unchanged; both (O12) **684 nJ** with zero standby, 90/90 unchanged.
- **Re-trim tolerance (B2, N = 20 per point, 1D sweeps ±200 mV):** within 5 points of nominal for V₁ −175…+100 mV and
  V₂ −25…+75 mV at |V_th| 0.65 V (nominal 15/20); V₁ −125…+200 mV and V₂ −200…+150 mV at 0.85 V (nominal 14/20). Read
  from the two 1D sweeps (the common-shift diagonal was not run, E10): the host must know |V_th| to **≈ 25 mV on the
  high side and ≈ 75 mV on the low side**. Beyond that: near-tie double latches (V₂ too low), race timeouts (V₂ too
  high: 0/20 at +200 mV, 0.65 V), and trips during integration (V₁ too low at 0.85 V: 15/20 runs at −200 mV).
- **V_th estimate error (B3, 20 MC dies, global |V_th| 0.55–0.95 V; B4 cells):** replica TFT RMS 4.2 / 6.3 mV (anchor
  20 / 35 mV), max 12.6 mV, µ-independent; host-only supply-current method RMS 3.1 / 5.4 mV, but +19 mV at µ ×0.5;
  host-only race-timing method RMS 11.1 / 14.4 mV, biased low (to −25 mV at 1.0 V). All three are inside the B2 band
  except a2 near its worst case. **Classification with method levels (E11.3, the 4 dies with the largest a2 error,
  20 samples each): every method matches ideal re-trim within 1 sample on every die** (13/13/13/13, 13/13/13/13,
  11/11/11/11, 12/12/11/11 for ideal/rep/a1/a2), with estimate errors up to −26 mV.
- **Aging map (B4, 3 × 3 grid, N = 20 per cell, PROXY inputs):** without re-trim the design fails completely from
  ΔV_th +0.2 V (0/20, every race times out), and at nominal |V_th| it gives 15 / 13 / 8 of 20 at µ ×1 / ×0.7 / ×0.5.
  **With ideal re-trim every drifted cell classifies: 12–14/20** (+0.2 V: 14 / 13 / 13; +0.35 V: 12 / 13 / 13 at
  µ ×1 / ×0.7 / ×0.5; 4/20 trips during integration at +0.35 V, µ ×1, strict 11/20). The one cell re-trim cannot fix
  is µ ×0.5 at nominal |V_th| (8/20): 8 of its 10 failures are races that do not finish in the 2500 µs window, because the rails
  must climb 0.77 V at a halved slope; at +0.2/+0.35 V the higher reset floor cuts that climb to 0.51/0.31 V and the race fits (§5.1).
  **Host-only fix tested:** T₁ and window × 1/µ at that cell gives 15/20 with all 20 outcomes identical to µ ×1 (E11.2).
- **Lower edge (B5, short runs):** stuck latches for |V_th| ≤ **0.541 V** (fixed levels; 0.542 V re-trimmed), a sharp
  1 mV edge. Mechanism: the trip driver X83 is not fully off because the comparator output only reaches `vls`
  (≈ 2.7–2.9 V). Releasing `rstb` at 50 µs (host-only) moves the edge to **0.477 V**; re-trim, lower calibration level
  and longer reset do not move it. 20-sample check of that fix: **no cost at nominal (20/20 outcomes identical,
  15/20)**, and 13/20 at 0.50 V (where baseline timing gives 0/20) with 3 weak, unlatched outputs.

## 2. Energy and power (B1)
Source: [b1_energy.json](summary/b1_energy.json), per sample: [b1_runs.csv](summary/b1_runs.csv). Accounting: DECISIONS E1.
All 90 test samples, Variant 3 at `fitc10`, warm start, baseline protocol with the campaign's 2500 µs race window
(3008 µs per classification). Instrumented runs reproduce the fitc10 Phase 1 outcomes on 90/90 samples (largest
trip-time difference 0.001 µs); current closure (sum of block ammeters vs source current) ≤ 2·10⁻⁸.

### 2.1 Energy per classification
| Quantity (N = 90) | Median | Range (min–max) |
|---|---|---|
| **Net energy into the die, all 11 sources** | **714 nJ** | 684–717 nJ |
| Driver-side cost (3.3 V host rail model, `host33`) | 722 nJ | 692–725 nJ |
| From VDD alone | 713.7 nJ | — |
| All host lines together (rows, rstr, rstb, phib, phi), net / host33 | ≈ 0.3 nJ / ≈ 7 nJ | — |
| Mean power over the classification | 237 µW | — |

- Host lines: the six row drivers deliver 0.07–0.15 nJ net each (0.6–1.2 nJ in the 3.3 V driver model); `rstr` −0.46 nJ net
  (it gets charge back from the five 400/20 reset-switch gates) but 1.7 nJ in the driver model; `rstb`, `phib`, `phi`
  ≤ 0.2 nJ. The die's energy is a static-current problem, not a switching one.

### 2.2 By phase (medians)
| Phase | Duration | Energy | Mean power |
|---|---|---|---|
| Reset (0–301 µs) | 301 µs | 82 nJ | 273 µW |
| Calibration (301–312.5 µs) | 11.5 µs | 5.8 nJ | 502 µW |
| C1 integrate | 195 µs | 64 nJ (58–70) | 330 µW |
| C2 race (to lock) | 889 µs (493–1148 race) | 205 nJ (118–269) | 230 µW |
| Post-lock (to end of window) | 1611 µs | 358 nJ (296–439) | 222 µW |

### 2.3 By block (medians, whole classification)
| Block | Energy | Share | Main devices |
|---|---|---|---|
| Reference | 379 nJ | 53 % | level-shift bias X65 (+ follower X66): 358 nJ; drift servo X61–X64: 21 nJ; dummy columns, sampler < 1 nJ |
| Latch and lock | 250 nJ | 35 % | ratioed latch loads (X84/X87 families): 192 nJ; lock/`win`/inverter: 58 nJ |
| Crossbar | 85 nJ | 12 % | rail charging + row gate charge |
| Comparators | 0.3 nJ | — | VDD side of the trip drivers; the comparator senses draw 23 nJ from `vls` (included in X65 above) |
| Rails and reset | −0.5 nJ | — | `rstr` gate charge returned |

- **Biggest consumers:** the level-shift bias X65 (≈ 120 µW while it conducts) and the ratioed-logic loads of the five
  latches (≈ 64 µW during a classification; in standby the four "loser" latches burn ≈ 4.4 µA each through their `nb` loads).

### 2.4 Dependence on race time
- With the fixed 2500 µs window the total does not depend on the race: slope −0.007 nJ/µs, r = −0.21.
- **Energy up to the lock** is linear in the race time: **169 nJ + 0.215 nJ/µs × race** (r = 0.998, N = 90; race
  493–1148 µs → 275–416 nJ). Everything after the lock (358 nJ median) is spent waiting for the window to close.

### 2.5 Standby
Idle levels: rows 3.3 V, `rstr` 3.3 V, `rstb` 3.3 V, `phib` 3.3 V, `phi` 0 V, VDD 3.3 V (E2). Six end states (one per
winning class + one double latch), simulated to 10⁵ s; all steady (< 0.01 % change over the last decade).
| Time after the classification | 0.1 ms – 1 s | 10 s | 100 s | ≥ 10³ s (steady) |
|---|---|---|---|---|
| Standby power, one class latched (5 end states, identical to 0.1 µW) | 198.7 → 198.3 µW | 196.9 µW | 184.1 µW | **98.2 µW** |
| Standby power, two classes latched (#24) | 188.0 µW | 186.2 µW | 173.4 µW | 87.5 µW |
- What changes: `ref` leaks up (1.39 → 2.62 V) and the rails leak down to ≈ 0 V, so `vls` rises to 3.23 V and the
  level-shift bias X65 drops from 108 to 26 µW. The four "loser" latch loads keep burning 58 µW whatever the state.
- **Consequence:** at any repetition period longer than a few ms, standby dominates. Energy per classification with VDD
  left on: 0.73 µJ back to back, 2.1 µJ at 100 /s, 20 µJ at 10 /s, **198 µJ at 1 /s**.

### 2.6 Host-only options (declared in E3 before running; each 90 samples)
| Option | Energy per classification, median (range) | Accuracy | Validity | Outcomes vs baseline | Idle |
|---|---|---|---|---|---|
| Baseline (2500 µs window, VDD on) | 714 nJ (684–717) | 62/90 = 68.9 % | 87/90 | — | 199 → 98 µW |
| **O1 adaptive race end** (rows off 50 µs after the first output edge) | **372 nJ (290–433), −48 %** | 62/90 | 86/90 | 1 changed: #37 (label 4) baseline class 1 → near-tie double latch | 199 → 98 µW (VDD on) |
| O2 VDD power-gated idle (cold start, baseline window) | 829 nJ (820–834), +16 % | 62/90 | 87/90 | 0 changed | 0 |
| **O12** = O1 + O2 | **684 nJ (591–754), −4 %** | 62/90 | 87/90 | 0 changed | 0 |
- O1 classification ends at 1469 µs (median) instead of 3008 µs; its warm start is its own (#81 chained, converged in
  3 runs; rail reset level 0.88 V vs 0.90 V for the baseline warm start). The outputs read at the stop time equal the
  end-of-window state on 90/90 samples.
- Cold start (O2, O12): the rails start below the p-type reset floor (0.11 V at the end of reset instead of 0.90 V),
  so the race is longer (median ≈ 1.9 ms) and costs more; classification outcomes are unchanged on all 90 samples.
- **Per classification including idle** ([b1_energy.json](summary/b1_energy.json) `energy_vs_period_nJ`):
  | Repetition period | 3.1 ms | 10 ms | 100 ms | 1 s | 10 s |
  |---|---|---|---|---|---|
  | Baseline, VDD on | 0.73 µJ | 2.1 µJ | 20 µJ | 198 µJ | 1.98 mJ |
  | O1, VDD on | 0.70 µJ | 2.1 µJ | 20 µJ | 198 µJ | 1.98 mJ |
  | O2, VDD off between | 0.83 µJ | 0.83 µJ | 0.83 µJ | 0.83 µJ | 0.83 µJ |
  | **O12, VDD off between** | **0.68 µJ** | **0.68 µJ** | **0.68 µJ** | **0.68 µJ** | **0.68 µJ** |
- **Reading:** for back-to-back operation O1 halves the energy; for anything slower than ≈ 300 classifications per
  second, switching VDD off between classifications (O12) is the lever that matters (×300 at 1 /s), at no accuracy cost on
  these 90 samples.
- Not evaluated (listed only): a shorter reset (≈ 27 nJ per 100 µs of reset at 273 µW; rail convergence would need
  checking), a lower VDD (moves every operating point; not a host-only trim).

## 3. Re-trim tolerance (B2)
Decisions: E4 (sweep), E10 (cut to 1D, 50 mV). Source: [b2_retrim.json](summary/b2_retrim.json), [b2_points.csv](summary/b2_points.csv).
20-sample subset, Variant 3 warm start, 2500 µs window. Offsets are from the formula levels (0.65 V: 1.82/2.40 V;
0.85 V: 1.62/2.20 V). Points at 25 mV steps finished before the cut are included.
<!-- B2_TABLE -->

**|V_th| 0.65 V** (zero offset: 15/20). Cells: correct / valid / strict (a trip during integration counts as a failure); failures.

| Offset (mV) | V₁ swept (V₂ formula) | V₂ swept (V₁ formula) |
|---|---|---|
| -200 | 13 / 18 / 11 (multi_latched 2); race 275 µs | 13 / 18 / 13 (multi_latched 2); race 318 µs |
| -175 | 14 / 19 / 13 (multi_latched 1); race 357 µs | 13 / 18 / 13 (multi_latched 2); race 351 µs |
| -150 | 15 / 20 / 14; race 436 µs | 13 / 18 / 13 (multi_latched 2); race 390 µs |
| -125 | 15 / 20 / 15; race 515 µs | 13 / 18 / 13 (multi_latched 2); race 437 µs |
| -100 | 15 / 20 / 15; race 591 µs | 13 / 18 / 13 (multi_latched 2); race 493 µs |
| -75 | 15 / 20 / 15; race 666 µs | 13 / 18 / 13 (multi_latched 2); race 561 µs |
| -50 | 15 / 20 / 15; race 738 µs | 13 / 18 / 13 (multi_latched 2); race 644 µs |
| -25 | 15 / 20 / 15; race 810 µs | 15 / 20 / 15; race 748 µs |
| +0 | 15 / 20 / 15; race 879 µs | 15 / 20 / 15; race 879 µs |
| +25 | 15 / 20 / 15; race 946 µs | 15 / 20 / 15; race 1046 µs |
| +50 | 15 / 20 / 15; race 1012 µs | 15 / 20 / 15; race 1264 µs |
| +75 | 15 / 20 / 15; race 1076 µs | 15 / 20 / 15; race 1552 µs |
| +100 | 14 / 19 / 14 (multi_latched 1); race 1137 µs | 13 / 18 / 13 (timeout 2); race 1821 µs |
| +125 | 13 / 18 / 13 (multi_latched 2); race 1197 µs | 8 / 10 / 8 (timeout 10); race 1969 µs |
| +150 | 13 / 18 / 13 (multi_latched 2); race 1255 µs | 3 / 4 / 3 (timeout 16); race 2212 µs |
| +175 | 13 / 18 / 13 (multi_latched 2); race 1310 µs | 1 / 1 / 1 (timeout 19); race 2307 µs |
| +200 | 13 / 18 / 13 (multi_latched 2); race 1364 µs | 0 / 0 / 0 (timeout 20) |

Band within 5 points of nominal: V₁ [-175, 100] mV, V₂ [-25, 75] mV.

**|V_th| 0.85 V** (zero offset: 14/20). Cells: correct / valid / strict (a trip during integration counts as a failure); failures.

| Offset (mV) | V₁ swept (V₂ formula) | V₂ swept (V₁ formula) |
|---|---|---|
| -200 | 10 / 14 / 3 (multi_latched 6); race -41 µs | 13 / 18 / 13 (multi_latched 2); race 187 µs |
| -150 | 10 / 14 / 7 (multi_latched 6); race 41 µs | 13 / 18 / 13 (multi_latched 2); race 225 µs |
| -125 | 13 / 17 / 9 (multi_latched 3); race 101 µs | 13 / 18 / 13 (multi_latched 2); race 249 µs |
| -100 | 13 / 18 / 10 (multi_latched 2); race 186 µs | 13 / 18 / 13 (multi_latched 2); race 278 µs |
| -75 | 14 / 19 / 12 (multi_latched 1); race 262 µs | 13 / 18 / 13 (multi_latched 2); race 313 µs |
| -50 | 14 / 19 / 13 (multi_latched 1); race 336 µs | 13 / 18 / 13 (multi_latched 2); race 356 µs |
| -25 | 14 / 19 / 14 (multi_latched 1); race 407 µs | 13 / 18 / 13 (multi_latched 2); race 410 µs |
| +0 | 14 / 19 / 14 (multi_latched 1); race 477 µs | 14 / 19 / 14 (multi_latched 1); race 477 µs |
| +25 | 13 / 18 / 13 (multi_latched 2); race 545 µs | 15 / 20 / 15; race 563 µs |
| +50 | 13 / 18 / 13 (multi_latched 2); race 611 µs | 15 / 20 / 15; race 674 µs |
| +75 | 13 / 18 / 13 (multi_latched 2); race 676 µs | 15 / 20 / 15; race 821 µs |
| +100 | 13 / 18 / 13 (multi_latched 2); race 738 µs | 15 / 20 / 15; race 1018 µs |
| +125 | 13 / 18 / 13 (multi_latched 2); race 798 µs | 15 / 20 / 15; race 1286 µs |
| +150 | 13 / 18 / 13 (multi_latched 2); race 856 µs | 13 / 18 / 13 (timeout 2); race 1461 µs |
| +175 | not run | 8 / 10 / 8 (timeout 8, none_latched 2); race 1483 µs |
| +200 | 13 / 18 / 13 (multi_latched 2); race 967 µs | 6 / 8 / 6 (timeout 12); race 1600 µs |

Band within 5 points of nominal: V₁ [-125, 200] mV, V₂ [-200, 150] mV.
<!-- /B2_TABLE -->

**Reading.**
- Accuracy is flat over a wide range: most points are 13–15/20 against a nominal 15 (0.65 V) and 14 (0.85 V). With
  N = 20 a 2-sample dip already leaves the "within 5 points" band, so the band edges are noisy; the failure *types* are
  the robust part.
- **V₂ too low** (more C2 overdrive): the race is faster, gaps between classes shrink in time, and two near-tie samples
  double-latch (13/20 from −50 mV at 0.65 V). This sets the tight −25 mV edge.
- **V₂ too high:** the race slows until it no longer finishes in the 2500 µs window (timeouts from +100 mV at 0.65 V,
  +150 mV at 0.85 V); a longer window would recover part of it (not run).
- **V₁ too low at 0.85 V:** more charge in C1, so strong samples trip during integration (1, 3, 6, 8, 10, 15 of 20 at −50 …
  −200 mV); the plain count hides this, the strict count (third number) does not.
- **|V_th| knowledge:** an estimate δ too high lowers V₁ and V₂ together by δ. From the 1D bands, the binding limits are
  V₂ −25 mV (0.65 V) for an overestimate and V₂ +75 mV (0.65 V) for an underestimate, i.e. **−25 / +75 mV**, assuming the
  two effects do not interact (not tested: E10 cut the diagonal).

## 4. How the host learns |V_th| (B3)
Decisions: E8 (+ amendment). Sources: [b3_estimates.json](summary/b3_estimates.json), [b3_offsets.json](summary/b3_offsets.json),
[b4_estimates.json](summary/b4_estimates.json); scripts `vthmeth.py`, `b3_mc.py`, `b4_estimates.py`.

### 4.1 What the host can observe
The host drives VDD, the six rows and the four timing lines, and reads the five latch outputs `na1–5` (the class
outputs). Two host-only observables carry |V_th|: (i) **time** from the start of C2 to the first output edge, which
depends on the C2 overdrive 3.3 − V₂ − |V_th|; (ii) the **VDD supply current** (needs a current meter on the host's
supply, no die change), which with `rstr` held low is the crossbar current flowing through the clamped rails. Both are
used below. A host that only reads logic levels with no timing has no |V_th| information.

### 4.2 Methods
| Method | Type | What the host does | Extraction |
|---|---|---|---|
| **rep** | circuit addition (Variant 3R, 135 TFTs) | one extra TFT, W/L 300/54 µm, own 3 pads; source 3.3 V, drain 0 V via current meter, gate at V_SG 1.4/1.7/2.0 V (DC) | √I = a(V_SG − \|V_th\| − I·R) solved for a, \|V_th\|, R |
| **a1** | host-only (+ supply current meter) | normal reset with `rstr` held low; `phib` off at 290 µs; rows ramp 3.3 → 1.3 V over 4 ms | same 3-point fit at ΔI_DD = 5/20/45 µA |
| **a2** | host-only (digital outputs + timer) | 4 calibration races with input x = 0: V₂ = 1.8/2.0 V, then V₂ = 3.3 − est − 0.45/0.30 V | square-law ratio of the first-edge times |
Each estimate is corrected by its own nominal-die offset (a design-time constant: rep −0.6 mV, a1 −32.3 mV, a2 −117 /
−39 mV per step). Levels then follow the build_A formula. Measurement noise and meter resolution are not modelled.
- **Replica stress:** its terminals see at most |V_GS| 2.0 V and |V_GD| 1.9 V during the measurement (host-applied), and
  are not connected otherwise; the classifier netlist is unchanged, so the fitc10 Phase 2 audit (0/134 > 3.5 V) stands.
- **a1 stress:** the ramp puts at most 2.0 V across crossbar gate-source; not run through the audit script.

### 4.3 Estimate error, Monte Carlo (20 dies; ASSUMED mismatch)
Size-scaled V_th mismatch (`pelgrom_vth`, anchors 20 and 35 mV, µ and R_C nominal), 10 dies per anchor, global |V_th|
stratified over 0.55–0.95 V (one die per 40 mV). Error = estimate − global |V_th|.
| Method | Anchor 20 mV: mean / RMS / max\|err\| | Anchor 35 mV: mean / RMS / max\|err\| |
|---|---|---|
| rep | −1.7 / 4.2 / 8.1 mV | −1.5 / 6.3 / 12.6 mV |
| a1 | −1.0 / 3.1 / 5.6 mV | −3.1 / 5.4 / 9.4 mV |
| a2 | −9.5 / 11.1 / 17.5 mV | −11.8 / 14.4 / 26.0 mV |

### 4.4 Estimate error on aged dies (global corners, no mismatch; B4 cells; aging PROXY)
| \|V_th\| (V) / µ | rep | a1 | a2 |
|---|---|---|---|
| 0.65 / ×1, ×0.7, ×0.5 | 0.0 / +0.1 / +0.1 mV | 0.0 / +10.9 / +19.3 mV | 0.0 / +3.6 / +5.8 mV |
| 0.85 / ×1, ×0.7, ×0.5 | −1.9 / −1.6 / −1.5 mV | −3.1 / +7.2 / +14.9 mV | −10.0 / −6.6 / −5.2 mV |
| 1.00 / ×1, ×0.7, ×0.5 | −6.5 / −6.2 / −5.9 mV | −5.9 / +3.3 / +9.4 mV | −24.9 / −22.8 / −23.3 mV |
(all 25 cells: rep ≤ 6.5 mV, a1 ≤ 19.3 mV, a2 ≤ 24.9 mV.)
- **Reading against B2:** the host may overestimate |V_th| by ≈ 25 mV and underestimate by ≈ 75 mV (from the 1D
  sweeps). The replica and a1 stay inside on every die and cell. a2 reads low (= levels too high, the tolerant side) by
  up to 26 mV, inside the underestimate side. On this evidence all three are adequate; a1 is the best host-only method
  and needs no circuit change, the replica is the most µ-independent.
### 4.5 Classification with each method's levels (E11.3, reduced)
The four MC dies with the largest a2 error (chosen for that, so this is a worst-case spot check, not an accuracy
estimate over the MC population), 20 samples each, levels from each estimate. Source: [b3_dies.csv](summary/b3_dies.csv),
`raw/b3/cls/`.
| Die (anchor, global \|V_th\|) | ideal | rep (err) | a1 (err) | a2 (err) | Failures |
|---|---|---|---|---|---|
| an20_d01 (20 mV, 0.862 V) | 13/20 | 13/20 (−6.7 mV) | 13/20 (−0.2 mV) | 13/20 (−16.7 mV) | 1 near-tie double latch each |
| an20_d03 (20 mV, 0.897 V) | 13/20 | 13/20 (−2.8 mV) | 13/20 (−1.3 mV) | 13/20 (−17.5 mV) | 2–3 near-tie double latches |
| an35_d09 (35 mV, 0.915 V) | 11/20 | 11/20 (+0.2 mV) | 11/20 (−8.8 mV) | 11/20 (−23.6 mV) | 3 near-tie double latches |
| an35_d10 (35 mV, 0.889 V) | 12/20 | 12/20 (−5.3 mV) | 11/20 (−9.4 mV) | 11/20 (−26.0 mV) | 2–3 near-tie double latches; 1 trip in C1 (except a2) |
- **Reading:** estimate errors up to 26 mV (all on the "levels too high" side) cost at most 1 sample of 20 against
  ideal knowledge, consistent with the B2 band. Accuracy on these dies (11–13/20) is set by the die's mismatch and
  high global |V_th|, not by the method. Not run: the other 16 MC dies.
- **Anomaly:** with `phib` held high from t = 0, a1's transient stalled at its start on die an35_d01 (solver, not
  circuit); the a1 sequence was changed and every a1 estimate recomputed (E8 amendment; changes < 2 mV elsewhere).

## 5. Aging maps (B4)
Decisions: E7, cut by E10 to ΔV_th ∈ {0, +0.20, +0.35} V × µ ∈ {×1, ×0.7, ×0.5}, policies "no re-trim" (1.82/2.40 V)
and "ideal re-trim" (formula at the true |V_th|). PROXIES: DNTT-family bias-stress shift +0.1…+0.35 V; mobility halving
after ≈ 8 months in air.
<!-- B4_TABLE -->

**No re-trim (1.82 / 2.40 V).** Cells: correct / valid of 20 (failures; median race from C2).

| ΔV_th \ µ | ×1 | ×0.7 | ×0.5 |
|---|---|---|---|
| +0.00 V (\|V_th\| 0.65) | 15 / 20; 879 µs | 13 / 18 (multi_latched 2); 1576 µs | 8 / 10 (none_latched 2, timeout 6, multi_latched 2); 2301 µs |
| +0.20 V (\|V_th\| 0.85) | 0 / 0 (timeout 20) | 0 / 0 (timeout 20) | 0 / 0 (timeout 20) |
| +0.35 V (\|V_th\| 1.00) | 0 / 0 (timeout 20) | 0 / 0 (timeout 20) | 0 / 0 (timeout 20) |

**Ideal re-trim (formula at the true |V_th|).** Cells: correct / valid of 20 (failures; median race from C2).

| ΔV_th \ µ | ×1 | ×0.7 | ×0.5 |
|---|---|---|---|
| +0.00 V (\|V_th\| 0.65) | 15 / 20; 879 µs | 13 / 18 (multi_latched 2); 1576 µs | 8 / 10 (none_latched 2, timeout 6, multi_latched 2); 2301 µs |
| +0.20 V (\|V_th\| 0.85) | 14 / 19 (multi_latched 1); 477 µs | 13 / 18 (multi_latched 2); 999 µs | 13 / 18 (multi_latched 2); 1594 µs |
| +0.35 V (\|V_th\| 1.00) | 12 / 17 (multi_latched 3); 167 µs | 13 / 18 (multi_latched 2); 558 µs | 13 / 18 (multi_latched 2); 981 µs |
<!-- /B4_TABLE -->

Source: [b4_aging.json](summary/b4_aging.json), [b4_map.csv](summary/b4_map.csv). Ideal re-trim levels: 1.82/2.40 V
(0.65 V), 1.62/2.20 V (0.85 V), 1.47/2.05 V (1.00 V). The ΔV_th = 0 row is the same runs for both policies.

**Reading.**
- **Without re-trim, V_th drift is fatal well inside the proxy range:** at +0.2 V the C2 overdrive 3.3 − V₂ − |V_th|
  is 0.05 V and no race finishes in the 2500 µs window (the fitc10 3A finding, now with µ loss on top).
- **With ideal re-trim, aging up to +0.35 V and µ ×0.5 costs 1–3 samples of 20** (12–14 vs 15 nominal); every failure
  is a near-tie double latch, plus 4 trips during integration at +0.35 V / µ ×1 (strict 11/20). Re-trim also *speeds
  up* the race at high |V_th| (median 167 µs at 1.00 V, µ ×1), which is why µ ×0.5 is harmless there.
- **The µ-limited cell is nominal |V_th| with µ ×0.7 / ×0.5** (13 and 8 of 20): races of 1.6 and 2.3 ms run into the
  2500 µs window (6 timeouts at ×0.5). Scaling T₁ and the window by 1/µ recovers µ ×0.5 completely (§5.1, E11.2).
- Combined with B3: the host's estimate error (≤ 26 mV, §4) is inside the B2 tolerance, so method re-trim should land
  near the ideal-re-trim map; this was not simulated (E10).

### 5.1 Why µ ×0.5 fails at nominal |V_th| but not at +0.20 / +0.35 V with ideal re-trim
From the existing B4 runs only (per-run JSONs and 1 µs waveforms; no new simulation). Script
`scripts/b4_mu_explain.py` → [b4_mu_explain.json](summary/b4_mu_explain.json). Medians over the 20 runs of each cell
(ideal re-trim; at 0.65 V it equals no re-trim). "Leading rail" = the highest rail at the start of C2; "trip level" = the
first tripper's rail voltage at its trip; "climb" = trip level − leading rail at C2.

| \|V_th\| / µ | Correct / valid | Rail reset level | C1 rise (leading rail) | Leading rail at C2 | Trip level | **Climb in C2** | C2 slope | **Race (median)** | Lock latency | Runner-up gap |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.65 V / ×1 | 15 / 20 | 0.90 V | 0.76 V | 1.66 V | 2.21 V | **0.55 V** | 0.56 mV/µs | **879 µs** | 19 µs | 74 µs |
| 0.65 V / ×0.5 | 8 / 10 | 1.04 V | 0.42 V | 1.46 V | 2.24 V | **0.77 V** | 0.26 mV/µs | **2301 µs** | 36 µs | 97 µs |
| 0.85 V / ×1 | 14 / 19 | 1.10 V | 0.76 V | 1.86 V | 2.15 V | **0.29 V** | 0.55 mV/µs | **477 µs** | 20 µs | 74 µs |
| 0.85 V / ×0.5 | 13 / 18 | 1.24 V | 0.42 V | 1.66 V | 2.16 V | **0.51 V** | 0.25 mV/µs | **1594 µs** | 38 µs | 74 µs |
| 1.00 V / ×1 | 12 / 17 | 1.24 V | 0.76 V | 2.00 V | 2.10 V | **0.10 V** | 0.55 mV/µs | **167 µs** | 22 µs | 75 µs |
| 1.00 V / ×0.5 | 13 / 18 | 1.38 V | 0.42 V | 1.80 V | 2.11 V | **0.31 V** | 0.25 mV/µs | **981 µs** | 43 µs | 76 µs |

1. **What halving µ does, at every |V_th|.** The C1 integration time is fixed by the host (T₁ = 170 µs), so each rail
   rises half as much in C1 (0.76 → 0.42 V). The re-trimmed V₂ keeps the C2 overdrive at 0.25 V, so the C2 slope also
   halves (0.55 → 0.25 mV/µs). The rails therefore enter C2 lower *and* climb half as fast.
2. **Resolution is not what fails.** Class separation at the end of C1 scales with µ, and so does the C2 slope, so the
   runner-up gap in *time* stays ≈ 74–97 µs at both mobilities. Lock latency roughly doubles (19 → 36–43 µs) but stays
   well under the gap. Near-tie double latches stay at 2/20 in every µ ×0.5 cell, the same as at µ ×1 (samples #17 and
   #31 recur).
3. **What fails at nominal |V_th| is the fixed 2500 µs race window.** The leading rail has to climb 0.77 V at
   0.26 mV/µs, so the median race is 2301 µs. **8 of the 10 failures are window failures:** 6 runs never trip
   (`timeout`), and 2 trip at 2473 and 2477 µs, too late for the latch to finish (lock latency 36 µs) before the window
   closes (`none_latched`). The 10 runs that finish are 8/10 correct, close to the µ ×1 rate.
4. **Why re-trimmed high-|V_th| cells escape it.** The rail reset level is the gate-grounded reset switch's floor and
   follows |V_th| (0.90 → 1.10 → 1.24 V at µ ×1). The trip level, set through `ref`/`vls`, barely moves (2.21 → 2.15 →
   2.10 V). So the climb in C2 shrinks with |V_th|: 0.55 → 0.29 → 0.10 V at µ ×1, and **0.77 → 0.51 → 0.31 V at
   µ ×0.5**. At the same halved slope, the µ ×0.5 race shortens to 1594 µs (0.85 V) and 981 µs (1.00 V), inside the
   window, and the cell is left with only its 2 near-tie failures. This is the lab-corner "window ≈ V_DD − 2|V_th|" rule
   working in the design's favour: the same shrinking margin that causes trips during integration at +0.35 V / µ ×1
   (4/20, the climb is only 0.10 V there) leaves room for a slow race at µ ×0.5.
5. **Side effect at nominal |V_th|, µ ×0.5:** the 300 µs reset is too short at half mobility, so the rails end reset at
   1.04 V instead of 0.90 V (the warm start leaves them near 3.2 V). That helps slightly (less climb), but it also makes
   the start state depend on the previous classification. Not quantified here.

**Consequence, tested (E11.2, declared before running).** The µ ×0.5 failure at nominal |V_th| is a host *timing*
limit, not a circuit one. With T₁ 170 → 340 µs and the race window 2500 → 5000 µs (both × 1/µ, ideal knowledge of µ;
20 runs, `raw/b4_aging/G_v065_m050_*_T1340_trace5000_*`): **15/20 correct, 20/20 valid, and all 20 outcomes identical
to the µ ×1 nominal runs**, against 8/20 without the change. Median race 1381 µs, longest 1947 µs: once T₁ is doubled
the rails enter C2 high enough that every race also fits the original 2500 µs window (the longer window was not
needed in these runs; T₁ alone was not tested separately). Lock latency stays ≈ 35 µs. The host needs a µ estimate for
this: the replica's 3-point fit and a1 both return the transconductance factor, but their µ accuracy was not evaluated.
The linear estimate climb ÷ slope (first 100 µs of C2) gives 3020 µs median for the unmodified cell, longer than the
measured 2301 µs because the rails accelerate during C2; it is used only as an ordering, not as a race-time model.

## 6. The lower |V_th| edge (B5)
Decisions: E6, cut by E10; partly restored by E11.1 (60 runs). Sources: [b5_full.json](summary/b5_full.json), [b5_short_*.json](summary/), probe runs `raw/b5_probe/`.

### 6.1 Mechanism
Probe runs (#81, fixed levels, every node saved) at |V_th| 0.45 and 0.55 V:
1. During reset `rstb` is low until 150 µs: XNP1–5 precharge every latch output `na` to VDD ("history equaliser").
2. After `rstb` releases, `na` can only fall through the latch-A load X84 (10/120 µm, gate-grounded; 6×-long in
   Variant 3, D4). Nothing actively pulls it down.
3. The trip driver X83 (200/10 µm, source VDD, gate `d`) is meant to be off. But its gate `d`, the comparator output,
   sits at the level-shifted reference `vls` (≈ 2.70–2.94 V), not at VDD: the 468/15 sense device clamps `d` to `vls`.
   So X83's "off" gate–source voltage is 3.3 − d ≈ 0.4–0.6 V.
4. At low |V_th|, X83 conducts in its "off" state, and the balance with the weak X84 leaves `na` above the 1.65 V trip
   level. When `rstr` releases at 312.5 µs (the `nb` pull-up X88 turns off), every latch whose `na` is still high
   regenerates into the latched state. At 0.45 V all five stay at ≈ 3.2 V (`stuck_latched`, the 3A result).

The threshold is input-independent (rows are inactive until 301 µs and calibration is the same for every sample), so it
was located with short runs (#81 to 330 µs; "stuck" = any `na` > 1.65 V at 320 µs) on a 10 mV grid from 0.44 to
0.66 V plus bisection to 1 mV.

### 6.2 Threshold and margin
| Host policy (E6) | Stuck for \|V_th\| ≤ | Works from | Highest `na` at 320 µs: 0.55 / 0.60 / 0.65 V | `ref` at 311 µs (0.65 V) |
|---|---|---|---|---|
| fixed levels (1.82/2.40 V, as 3A) | **0.541 V** | **0.542 V** | 1.58 / 1.25 / 1.11 V | 1.38 V |
| formula levels (re-trimmed) | 0.543 V | 0.543 V | 1.58 / 1.25 / 1.11 V | 1.38 V |
| **rstb50**: `rstb` released at 50 µs instead of 150 µs | **0.477 V** | **0.478 V** | 1.12 / 0.96 / 0.93 V | 1.56 V |
| Vcal −200 mV (calibration level only) | 0.541 V | 0.542 V | 1.58 / 1.25 / 1.11 V | 1.39 V |
| Vcal −400 mV | 0.541 V | 0.542 V | 1.58 / 1.25 / 1.11 V | 1.40 V |
| rext300: reset phase 300 µs longer | 0.540 V | 0.541 V | 1.57 / 1.20 / 0.98 V | 1.38 V |
- **The edge is sharp:** 1 mV separates stuck from working on every policy (monotonic over the whole grid).
- **The margin is thin above the edge:** at 0.55 V the highest `na` is 1.58 V at the start of trip counting, 70 mV
  under the trip level. At nominal it is 1.11 V.
- **Re-trimming the levels does not move the edge** (+1 mV). Nor does a lower calibration level: it raises `ref` only
  at 302–310 µs, after the `na` decay window. Nor does a longer reset: below the edge `na` settles at an equilibrium
  above 1.65 V, so more time doesn't help.
- **Releasing `rstb` earlier moves the edge by −65 mV.** Mechanism (short runs, 0.50 V): `rstb` also gates the C_ref
  reset switch X69. Releasing it at 50 µs stops `ref` at 0.96 V instead of 0.70 V during the decay window, so `vls`
  and `d` rise by ≈ 0.10 V and X83 is further off. Side effect: `ref` at the end of sampling is 0.18 V higher at nominal
  (1.56 vs 1.38 V), which moves the race threshold. Its 20-sample accuracy cost was not run (E10).

### 6.3 Twenty-sample check of the `rstb` fix (E11.1)
| Policy | \|V_th\| | Correct / valid of 20 | Failures | Median race | Note |
|---|---|---|---|---|---|
| baseline timing, fixed levels | 0.55 V (lowest working grid point) | 14 / 19 | 1 near-tie double latch | 424 µs | — |
| **`rstb` released at 50 µs** | **0.50 V** (stuck at baseline timing) | **13 / 17** | 3 `none_latched` | 372 µs | outputs ambiguous, see below |
| **`rstb` released at 50 µs** | **0.65 V (nominal)** | **15 / 20** | none | 983 µs (baseline 879) | **20/20 outcomes identical to baseline** |
- **No accuracy cost at nominal** on these 20 samples. The only change is a ≈ 100 µs longer race (`ref` ends sampling
  at 1.56 V instead of 1.38 V), i.e. ≈ +22 nJ to the lock at the B1 rate of 0.215 nJ/µs (estimate, not instrumented).
- **At 0.50 V the fix makes the die classify (13/20) where baseline timing gives 0/20**, but the margin is thin. In the
  3 invalid runs (#72, #81, #84) two classes trip and neither latch completes: the outputs hover at `na` ≈ 1.5–1.7 V
  with `nb` still high until the end of the window. The short runs show why: at 0.50 V the resting `na` is already
  1.44 V at 320 µs, only 0.2 V under the trip level, so latching is weak.
- **Reading:** the host-only fix moves the hard edge from 0.541 to 0.477 V and costs nothing measurable at nominal, but
  between ≈ 0.48 and ≈ 0.52 V the latch outputs are marginal. A circuit fix (§8 item 5) is still needed for margin.

## 7. What this does not show
- **Not measured hardware.** Simulation only; `fitc10` is a reconstructed corner (C10-DNTT on Si, currents read by eye);
  JOFF and LOV not fitted; the Variant 3 sizing is rebuilt from the author's decisions.
- **Energy:** no layout parasitics, pad/ESD or wiring capacitance, no host-driver losses beyond the 3.3 V-rail model;
  the energy is dominated by static current through compact-model devices whose subthreshold and contact behaviour is
  not fitted. Standby depends on leakage (JOFF, the 1 TΩ dummy resistors), which is the least certain part of the model.
- **Aging inputs are proxies** (family literature ranges), applied as a uniform global shift / mobility factor with no
  mismatch growth, no R_C change and no time dependence.
- **Re-trim tolerance:** N = 20 per point, so "within 5 points" is one sample; 1D only (the common shift of both levels,
  which is what an |V_th| error produces, was not simulated); one warm start for every point.
- **V_th learning:** noise-free current and time measurements; design-time offsets taken from the same compact model
  (model error between the host's correction and the real device is not represented); mismatch is assumed
  (`pelgrom_vth` anchors 20–35 mV); classification with the estimated levels only on 4 hand-picked dies.
- **Lower edge:** thresholds from short runs on one sample; 20-sample accuracy only at 0.50, 0.55 and 0.65 V
  (not the full 0.45–0.55 V grid); the energy cost of the `rstb` fix is an estimate.
- **Weights:** results apply to `F_hw_m4_firstpass.npy` only.

## 8. Proposals (separate from the results; none simulated unless stated)
1. **Adaptive race end (O1) and VDD power gating (O12)** — host-only, evidence §2.6 (simulated, 90 samples each).
1b. **T₁ (and race window) scaled by 1/µ** — host-only; recovers µ ×0.5 at nominal |V_th| (15/20, outcomes identical to
   µ ×1; §5.1, 20 samples). Needs a µ estimate (replica or a1 transconductance; accuracy not evaluated).
2. **B3 classification on the remaining 16 MC dies** (4 level sources × 20 samples) for a population accuracy per
   method — not run; the 4 worst-a2 dies (§4.5) show no method penalty beyond 1 sample.
3. **Replica TFT, Variant 3R** — +1 TFT (135), own pads, ≤ 2.0 V gate stress; estimate error §4.3–4.4. Not needed on
   this evidence if the host has a supply-current meter (a1).
4. **`rstb` released at 50 µs** — host-only; moves the stuck edge from 0.541 to 0.477 V (§6.2) with no accuracy cost
   at nominal on 20 samples (§6.3); latch outputs are marginal between ≈ 0.48 and 0.52 V.
5. **Circuit fixes for the lower edge (not run):** drive the comparator output `d` to VDD when idle (e.g. a pull-up
   gated by `rstr`), a stronger `na` reset device (an `na` pull-down gated by `rstr`/`rstb` instead of relying on X84),
   or a shorter-L X84; each adds 0–5 TFTs and needs a stress audit.
6. **Lower static power (circuit):** the level-shift bias X65 (≈ 120 µW while conducting) and the ratioed latch loads
   (≈ 64 µW) are 88 % of the energy; a duty-cycled bias or non-ratioed latch would cut it. Not evaluated.
