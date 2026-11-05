# Tortoise host-v2 study: host protocol v2 (Variant 3 at `fitc10`, old weights)

**Status: complete (2026-10-29 ≈ 05:30 UTC).** All phases C1–C6 run in full, plus the declared extension C6b (H5).
Post-freeze deviations: H4.1 (solver fallback, simulation setting), H4.2 (early-end timer as simulated; 0 runs changed).
Circuit frozen: Variant 3 at `fitc10`, weights `rev10/eval/F_hw_m4_firstpass.npy`; **only the host protocol changes.**
Protocol v2 was frozen in [DECISIONS.md](DECISIONS.md) H2 (commit `8948461`) before any evaluation run, after the
development checks H1 on training samples. Every number below is recomputed from per-run JSONs by `scripts/summ_phases.py`
(and `scripts/stress.py` for C2). Aging inputs are **literature proxies**. Nothing here is verified or validated.

## 1. Summary
<!-- SUMMARY -->
- **C1 nominal (N = 90 test samples):** v2 **62/90 = 68.9 %** (Wilson 95 % 58.7–77.5 %), validity 87/90 (90.7–98.9 %);
  **per-sample outcomes identical to v1 on 90/90** (exact McNemar p = 1.0). Back-to-back chain (N = 10): 10/10 identical
  to the independent runs, largest trip shift 0.003 µs (v1: 4.1 µs).
- **Energy (C1, N = 90):** **588 nJ per classification** (median; range 499–655 nJ) against 714 nJ (684–717) for v1;
  **standby 0** with VDD off (v1: 98–199 µW). One calibration session ≈ 3.0 µJ (partly estimated); amortised over 100
  classifications 618 nJ each.
- **C2 stress (5 runs, 134 TFTs, power-up + classification + power-down + 1 s off):** **0 TFTs above 3.5 V**; worst
  3.30 V (margin 0.20 V); crossbar max 3.03 V (v1 2.43 V); internal nodes go to −2.2 V at power-down (new).
- **C3 aging map (25 cells × 20, PROXY inputs, learned estimates):** **every cell classifies, 13–15/20**; pooled
  351/500 = 70.2 % (66.1–74.0 %). µ ×0.5 at 0.65 V: 15/20 (v1 8/20); ΔV_th +0.2…+0.35 V: 13–15/20 (v1 without re-trim
  0/20; v1 with ideal re-trim 12–14/20). a1 |V_th| error −4.4…+8.5 mV, µ̂ −1…+12 % (mostly high). One cell flagged by the race
  cross-check (1.00 V/µ ×0.5, +67 mV) is a false alarm: ideal knowledge gives the same 13/18.
- **C4 mismatch (3B-V anchor 20 mV, 5 dies × 20):** v2 **64/100** (54.2–72.7 %) vs v1 64/100; validity 97 vs 95;
  94/100 outcomes identical; McNemar p = 1.0. Per-die |V_th| estimates within −1.2…+2.4 mV.
- **C5 history at µ ×0.5 (20-step chain):** **20/20 outcomes identical** to independent runs (race shifts ≤ 0.012 µs);
  the v1 reset length (300 µs) gives the same 20 outcomes, so the reset extension has no effect under power gating.
- **C6 lower edge (N = 20 per point): FAILURE.** 0/20 at every point 0.45–0.55 V (all latches stuck) and 0/20 at
  0.57 V (`none_latched`); 15/20 at 0.59 and 0.61 V (C6b extension). **v2 moves the lower edge up** from 0.541 V (v1,
  fixed levels; 14/20 at 0.55 V) to 0.57–0.59 V: power gating removes the residual `ref` charge that the energy/host study's
  `rstb`-50 µs fix relied on, and the early-end timer then counts a slowly decaying `na` as an output.
<!-- /SUMMARY -->

## 2. Host protocol v2 (frozen definition: DECISIONS H2)
The host sees only its own line levels and timer, the five class outputs `na1–5`, and a current meter on its own VDD
supply. It never uses the simulator's |V_th| or µ except in runs labelled **ideal**.

| Element | v1 (energy/host study baseline) | **v2** |
|---|---|---|
| Between classifications | VDD on (standby 98–199 µW) | **VDD and all lines 0 V for 1 s** (power gating, (d)) |
| Start of a classification | warm (previous end state) | power-up ramp 0–10 µs from the **1 s-off state** |
| \|V_th\| knowledge | none (fixed 1.82/2.40 V) or ideal | **learned**: a1 supply-current method (V̂), formula levels ((a)) |
| Cross-check | — | two x = 0 calibration races, square-law estimate; flag if \|Δ\| > 50 mV |
| µ knowledge | none | **learned**: µ̂ = ΔI_DD(V̂_raw + 0.6 V) / nominal; **k = clip(1/µ̂, 1, 2.5)** ((b)) |
| Reset length | 300 µs | 300·k µs |
| `rstb` release | 150 µs | **50 µs** ((e)) |
| T₁ | 170 µs | 170·k µs (WMIN 20 µs unchanged) |
| Race end | fixed 2500 µs window | **early end** ((c)): rows off 50·k µs after the first output; read 10·k µs later; timeout 4000·k µs |

Calibration session (once per die/condition): long off → a1 (4.3 ms row ramp, `rstr` low) → 1 s off → race a → 1 s off →
race b → 1 s off → classifications. Design-time constants come from the nominal die (|V_th| 0.65 V, µ ×1, no mismatch):
c_a1 = −50.88 mV, I_ref = 31.44 µA, c_race = −34.48 mV ([design_constants.json](summary/design_constants.json)).

**What the pre-freeze checks changed (H1-outcome, training samples, development runs):** the a1 offset had to be
re-derived (cold power-up shifts the raw estimate by 19 mV); a² from the a1 fit is not a usable µ estimate under cold
start, so the current-ratio estimator was chosen (dev-corner error +0…+12 %, biased high); the early-end delay D must
scale with k (fixed 50 µs gave `none_latched` 5/5 at µ ×0.5); the timeout window was raised to 4000·k µs because cold-start
races are ≈ 750 µs longer; a "cold" start after 1 s off is not an all-zero start (rails at 0.23 V, latch nodes below 0 V).

## 3. C1: nominal operation (N = 90) and back-to-back chain
Source: [c1_nominal.json](summary/c1_nominal.json), per sample [c1_runs.csv](summary/c1_runs.csv), runs `raw/C1/`.
Calibration on the nominal die: V̂ = 0.650 V, µ̂ = 1.000, k = 1, levels 1.82/2.40 V. **This die is also the design-time
die, so these estimates equal the design constants by construction** (no estimation error can show here; C3, C4 and C6
test the estimates).

| Measure (N = 90) | v1 (fitc10 Phase 1) | **v2** |
|---|---|---|
| Accuracy | 62/90 = 68.9 % (58.7–77.5) | **62/90 = 68.9 % (58.7–77.5)** |
| Validity | 87/90 (90.7–98.9) | 87/90 (90.7–98.9) |
| Failures | multi-latched 3 (#24, #25, #42) | multi-latched 3 (same samples) |
| Per-sample outcome | — | **90/90 identical** (also 90/90 identical to the energy/host study's O12) |
| Paired correct (both / v2 only / v1 only / neither) | — | 62 / 0 / 0 / 28; exact McNemar p = 1.0 |
| Race from C2, median (range) | 870 µs (493–1148) | 1626 µs (1251–1904); +757 µs on every sample (755–758) |
| Lock latency, median | 19.2 µs | 23.9 µs |
| Runner-up gap (slope-extrapolated), v2/v1 per sample | — | median 1.002 (5–95 %: 0.99–1.03), N = 90 |
| Time per classification (to the read) | 3008 µs | 2194 µs median (1819–2472) |

- **Why the race is 757 µs longer:** after 1 s off the rails start at 0.23 V and reach only 0.33 V at the end of
  reset, instead of the warm reset floor 0.90 V; the climb in C2 is longer. Class separation is unchanged (runner-up
  ΔV and slope-extrapolated gap within ±3 % of v1 on every sample), so no outcome changes.
- **Gap metric under the early end:** the "reach" gap of `common.metrics` needs the runner-up to reach the winner's
  trip level before the simulation stops; with the early end that happens on only 30/90 runs, so v2 gaps are compared
  with the slope-extrapolated definition (same function, `gap_slope_us`).

### 3.1 Energy and standby (post-processing of the 90 C1 runs; the energy/host study's E1 accounting)
| Quantity (N = 90) | v1 baseline (B1) | The energy/host study's O12 | **v2** |
|---|---|---|---|
| Net energy per classification, all 11 sources | 714 nJ (684–717) | 684 nJ (591–754) | **588 nJ (499–655)** |
| Driver-side (3.3 V host rail model) | 722 nJ | — | 595 nJ (506–662) |
| Standby | 98–199 µW (VDD on) | 0 | **0** (VDD off) |
| Per classification incl. idle at 1 /s | ≈ 198 µJ | 0.68 µJ | **0.59 µJ** |

- By phase (medians): reset 90 nJ (300 µs), sampling 6 nJ, C1 69 nJ, C2 to the lock 416 nJ, lock → read 9 nJ.
  Energy ≈ 70 nJ + 0.237 nJ/µs × read time (r = 0.999).
- By block: reference 342 nJ (level-shift bias X65/X66 327 nJ), latch and lock 179 nJ, crossbar 67 nJ, comparators
  1.3 nJ. VDD supplies 99.7 %. Current closure ≤ 3·10⁻⁸.
- v2 vs O12 (both power-gated with an early end): v2 is 96 nJ lower (median). Most of it is the start state: O12
  started from all-zero, v2 from the 1 s-off state (rails at 0.23 V), which shortens the race by ≈ 260 µs
  (O12 median race 1889 µs, v2 1626 µs; ≈ 62 nJ at 0.237 nJ/µs). This is an attribution estimate, not a separate run.
- **Calibration session:** a1 1.92 µJ (VDD, measured), two cross-check races ≈ 0.42 + 0.66 µJ (estimated from the
  E-vs-read-time fit, not instrumented): ≈ 3.0 µJ. Per classification including calibration: 3.6 µJ if calibrating
  every time, 887 nJ every 10, 618 nJ every 100, 591 nJ every 1000.
- **Not counted:** energy during the 10 µs power-down (returned charge is not credited, as in the energy/host study), host
  electronics, the I_DD meter.

### 3.2 Back-to-back chain (samples 30–39, 1 s off between)
Each step starts from the simulated 1 s-off state after the previous one (step 0 from the calibration start state).
- **Outcomes: 10/10 identical to the independent runs** (v1 chain: 10/10). Accuracy on the 10: 9/10 (#37, label 4,
  classified 1, as in v1).
- **Largest first-trip shift 0.003 µs, rail reset level shift < 0.01 mV** (v1 chain: 4.1 µs and 5.5 mV). Power gating
  removes the history channel that v1's warm start carried: after 1 s off the rails equalise (0.231 V) and the `na`
  history is erased by the `rstb` precharge (DECISIONS H1-outcome 6). Only steps 1–9 carry information.

## 4. C2: stress audit (5 runs)
Source: [c2_stress.json](summary/c2_stress.json), per device and run [c2_devices.csv](summary/c2_devices.csv); script
`scripts/stress.py`. Runs: the fitc10 Phase 2 input picks (maxsum #17, minsum #61, maxcol #29, mincol #1) and #31 after
#30 (1 s off between), nominal die, nominal calibration. Each run is audited over (i) the power-up ramp and the whole
classification to the read, every top-level node at full resolution, and (ii) the power-down ramp and the 1 s off.
Max |V_GS| and |V_GD| from terminal voltages, all 134 TFTs (crossbar instances included).

| | v1 (fitc10 Phase 2) | **v2** |
|---|---|---|
| TFTs above 3.5 V | 0/134 | **0/134** (all 5 runs, both segments) |
| Worst device | X80, 3.339 V (`win` overshoot in reset) | **3.300 V** (XNP1–5, XWR, X69, X75–79: a gate at 0 V against VDD, or the reverse); X80 3.274 V |
| Crossbar maximum | 2.43 V (row step into calibration) | **3.03 V** (X1, at 10 µs: end of the power-up ramp) |
| Lowest node voltage | ≥ 0 V ("no negative voltages anywhere") | **−2.04 V** during the classification (start state), **−2.20 V** in the power-down |
| Power-down + 1 s off, worst | — | 3.30 V (idle levels at t = 0); crossbar 2.02 V |

- **The margin is 0.20 V, as in v1, but the crossbar's margin falls from 1.07 V to 0.47 V:** at the end of the power-up
  ramp the rows are at 3.3 V while the rails sit at ≈ 0.27 V (v1 rails start at ≈ 0.9 V).
- **Negative nodes are new.** The 10 µs power-down ramp couples `na`, `nb`, `lockb` (and `n1`) below ground (to
  −2.2 V); they are still negative 1 s later (`lockb` −1.87 V) and the next power-up starts from there. No device
  exceeds 3.5 V because of it in these runs, but the base design's rule "no negative voltages anywhere" no longer
  holds under power gating. A slower or sequenced power-down was not tried.
- All five classifications gave the same outcome as their C1 runs (17 → 4, 61 → 1, 29 → 5, 1 → 1, 31 → 2).

## 5. C3: aging map (5 × 5 cells × 20 samples = 500 runs, learned estimates; aging inputs are PROXIES)
Source: [c3_aging.json](summary/c3_aging.json), runs `raw/C3/`, calibrations `raw/cal/v*_m*/`. Global corners
(uniform ΔV_th from 0.65 V and µ factor; no mismatch), the 20-sample subset, each cell with its own calibration session.
Levels and timing are the host's learned values in every cell.

**v2, learned estimates.** Cells: correct / valid of 20 (failures; strict count if trips in C1).

| ΔV_th \ µ | ×1 | ×0.85 | ×0.7 | ×0.6 | ×0.5 |
|---|---|---|---|---|---|
| +0.00 V (0.65) | 15 / 20 | 15 / 20 | 15 / 20 | 15 / 20 | 15 / 20 |
| +0.10 V (0.75) | 15 / 20 | 15 / 20 | 15 / 20 | 15 / 20 | 15 / 20 |
| +0.20 V (0.85) | 14 / 19 (multi_latched 1) | 14 / 19 (multi_latched 1) | 14 / 19 (multi_latched 1) | 14 / 19 (multi_latched 1) | 15 / 20 |
| +0.30 V (0.95) | 13 / 18 (multi_latched 2) | 13 / 18 (multi_latched 2) | 13 / 18 (multi_latched 2) | 13 / 18 (multi_latched 2) | 13 / 18 (multi_latched 2) |
| +0.35 V (1.00) | 13 / 18 (multi_latched 2) | 13 / 18 (multi_latched 2) | 13 / 18 (multi_latched 2) | 13 / 18 (multi_latched 2) | 13 / 18 (multi_latched 2) |

**Calibration per cell:** |V_th| error (mV) / µ̂ ÷ µ / k / race cross-check error (mV), flag.

| ΔV_th \ µ | ×1 | ×0.85 | ×0.7 | ×0.6 | ×0.5 |
|---|---|---|---|---|---|
| +0.00 V | +0.0 / 1.000 / 1.00 / +0.0 | +3.2 / 1.024 / 1.15 / +2.1 | +5.7 / 1.049 / 1.36 / +4.4 | +6.8 / 1.066 / 1.56 / +6.0 | +6.6 / 1.081 / 1.85 / +7.7 |
| +0.10 V | -1.0 / 0.997 / 1.00 / +1.4 | +1.5 / 1.020 / 1.15 / +4.1 | +3.2 / 1.044 / 1.37 / +7.0 | +3.3 / 1.059 / 1.57 / +9.3 | +1.9 / 1.073 / 1.86 / +11.8 |
| +0.20 V | -3.3 / 0.991 / 1.01 / +10.2 | -1.2 / 1.014 / 1.16 / +13.7 | -0.0 / 1.038 / 1.38 / +17.9 | -0.2 / 1.054 / 1.58 / +21.2 | -1.6 / 1.069 / 1.87 / +25.2 |
| +0.30 V | -4.4 / 0.988 / 1.01 / +26.1 | -1.3 / 1.017 / 1.16 / +31.0 | +2.1 / 1.051 / 1.36 / +37.2 | +4.1 / 1.078 / 1.55 / +42.7 | +4.6 / 1.104 / 1.81 / +49.9 |
| +0.35 V | -1.2 / 0.999 / 1.00 / +37.0 | +3.5 / 1.035 / 1.14 / +43.2 | +7.4 / 1.074 / 1.33 / +51.3 | +8.4 / 1.100 / 1.52 / +58.2 | +6.6 / 1.121 / 1.78 / +67.1 **FLAG** |

**Race from C2, median (µs), learned.**

| ΔV_th \ µ | ×1 | ×0.85 | ×0.7 | ×0.6 | ×0.5 |
|---|---|---|---|---|---|
| +0.00 V | 1636.5 | 1900.2 | 2269.5 | 2632.3 | 3150.9 |
| +0.10 V | 1460.9 | 1695.3 | 2058.1 | 2405.1 | 2898.7 |
| +0.20 V | 1278.6 | 1498.1 | 1820.5 | 2128.4 | 2590.2 |
| +0.30 V | 1083.5 | 1267.2 | 1527.7 | 1769.9 | 2114.8 |
| +0.35 V | 966.3 | 1128.9 | 1355.7 | 1583.9 | 1918.0 |

**Ideal-knowledge reference (failing cells only).**

| Cell | learned | ideal |
|---|---|---|
| 1.00 V / ×0.5 | 13 / 18 (multi_latched 2) | 13 / 18 (multi_latched 2) |

**v1 vs v2 on the energy/host study's 3 × 3 cells** (correct / valid of 20).

| Cell | v1 no re-trim | v1 ideal re-trim | **v2 learned** |
|---|---|---|---|
| 0.65 V / ×1 | 15 / 20 | 15 / 20 | 15 / 20 |
| 0.65 V / ×0.7 | 13 / 18 (multi_latched 2) | 13 / 18 (multi_latched 2) | 15 / 20 |
| 0.65 V / ×0.5 | 8 / 10 (multi_latched 2, none_latched 2, timeout 6) | 8 / 10 (multi_latched 2, none_latched 2, timeout 6) | 15 / 20 |
| 0.85 V / ×1 | 0 / 0 (timeout 20) | 14 / 19 (multi_latched 1) | 14 / 19 (multi_latched 1) |
| 0.85 V / ×0.7 | 0 / 0 (timeout 20) | 13 / 18 (multi_latched 2) | 14 / 19 (multi_latched 1) |
| 0.85 V / ×0.5 | 0 / 0 (timeout 20) | 13 / 18 (multi_latched 2) | 15 / 20 |
| 1.00 V / ×1 | 0 / 0 (timeout 20) | 12 / 17 (multi_latched 3) | 13 / 18 (multi_latched 2) |
| 1.00 V / ×0.7 | 0 / 0 (timeout 20) | 13 / 18 (multi_latched 2) | 13 / 18 (multi_latched 2) |
| 1.00 V / ×0.5 | 0 / 0 (timeout 20) | 13 / 18 (multi_latched 2) | 13 / 18 (multi_latched 2) |



**Reading.**
- **Every cell classifies.** Pooled 351/500 = 70.2 % (Wilson 66.1–74.0 %), validity 476/500; per cell 13–15/20
  against 15/20 at nominal. No run trips during integration (v1 ideal re-trim had 4/20 at 1.00 V/µ ×1).
- **Mobility loss is fully compensated by the learned k** in this grid: at 0.65 and 0.75 V every µ column gives 15/20
  and **all 20 per-sample outcomes are identical to the nominal cell** (also at 0.85 V/µ ×0.5). v1 gives 13/20 at
  µ ×0.7 and 8/20 at µ ×0.5 (6 timeouts); the energy/host study's ideal-µ T₁ × 2 test gave 15/20.
- **|V_th| drift is handled by the learned levels:** 14–15/20 at +0.2 V, 13/20 at +0.3/+0.35 V. The losses are 1–2
  near-tie double latches per cell (the same samples recur: at 0.95/1.00 V two outcomes differ from nominal in every µ
  column), the same failure type and similar counts as v1 with *ideal* re-trim (12–14/20).
- **Estimates:** a1 |V_th| error −4.4 … +8.5 mV over the 25 cells (inside the ≈ −25/+75 mV B2 tolerance); µ̂ reads
  −1…+12 % (high in 22 of 25 cells, largest at high |V_th| and low µ), so k is up to 11 % short of 1/µ; it did not cost accuracy here.
- **Cross-check:** the race-timing estimate reads increasingly high with |V_th| (+26…+67 mV at 0.95–1.00 V) and
  **flags 1.00 V/µ ×0.5 (+67 mV) although a1 is off by only +6.6 mV there: a false alarm.** By the frozen rule (H3) the
  flagged cell counts as failing and gets the ideal reference: **ideal knowledge gives the same 13/18 there** (same
  failure type), so nothing was lost to the learned estimates. The cross-check, as defined, would trigger a
  re-calibration or service call on an aged die whose estimate is fine.
- **Race time** grows from 966 µs (1.00 V/µ ×1) to 3151 µs (0.65 V/µ ×0.5); with the early end the classification
  time follows it (no fixed window). Lock latency at µ ×0.5 is 45 µs (median), inside the 50·k = 92 µs early-end delay.
- Not shown: aging with mismatch, mixed per-device drift, R_C change, and µ above ×1.

## 6. C4: mismatch (3B-V, anchor 20 mV, 5 dies × 20 samples = 100 runs)
Source: [c4_mismatch.json](summary/c4_mismatch.json), runs `raw/C4/`, calibrations `raw/cal/v0650_m100_an20d0*/`.
Size-scaled V_th mismatch (`pelgrom_vth`, anchor 20 mV, µ and R_C nominal), the fitc10 3B-V dies (seeds 20001–20005),
global |V_th| 0.65 V. Each die runs its own calibration session; the |V_th| error is against the global 0.65 V.

| Die (seed) | \|V_th\| err (mV) / µ̂ / k / flag | v1 3B-V | **v2** | paired: both / v2 only / v1 only / neither (McNemar p) |
|---|---|---|---|---|
| d1 (20001) | +0.4 / 1.002 / 1.00 / False | 13 / 19 (multi_latched 1) | 12 / 19 (multi_latched 1) | 12 / 0 / 1 / 7 (1.0) |
| d2 (20002) | +1.5 / 0.999 / 1.00 / False | 13 / 19 (multi_latched 1) | 13 / 19 (multi_latched 1) | 13 / 0 / 0 / 7 (1.0) |
| d3 (20003) | +2.4 / 1.001 / 1.00 / False | 14 / 19 (multi_latched 1) | 15 / 20 | 14 / 1 / 0 / 5 (1.0) |
| d4 (20004) | -1.2 / 1.006 / 1.00 / False | 11 / 19 (multi_latched 1) | 11 / 19 (multi_latched 1) | 11 / 0 / 0 / 9 (1.0) |
| d5 (20005) | -0.1 / 0.999 / 1.00 / False | 13 / 19 (multi_latched 1) | 13 / 20 | 13 / 0 / 0 / 7 (1.0) |
| **pooled** | | 64/100 [0.5424, 0.7273] valid 95 | 64/100 [0.5424, 0.7273] valid 97 | 63 / 1 / 1 / 35 (1.0) |


- **v2 equals v1 under mismatch:** pooled 64/100 both (Wilson 54.2–72.7 %); validity 97/100 (91.6–99.0) vs 95/100;
  **94/100 per-sample outcomes identical**; per die within ±1 sample; McNemar p = 1.0 on every die and pooled.
- **Each die learns its own values:** |V_th| within −1.2…+2.4 mV of the global value, µ̂ within 0.6 %, so k = 1.00 and
  levels within 3 mV of nominal on every die; no flags. The race cross-check agrees within −5.0…+0.2 mV.
- **Die d04 runs on the timer's tolerance:** on all 20 of its runs one latch node is still above 1.65 V for 6.1 µs
  when counting starts (§8 mechanism 3); the integrating timer (H4.2) absorbs it, a literal "first output" host would
  abort all 20. Its accuracy (11/20) is the same as under v1.
- **Solver:** the 1 s-off simulations of die d01's calibration needed the NOOPITER fallback (H4.1, 2 runs); no
  classification run did.

## 7. C5: history dependence at µ ×0.5 (2 chains × 20 runs)
Source: [c5_history.json](summary/c5_history.json), runs `raw/C5/`. Cell |V_th| 0.65 V, µ ×0.5, its C3 calibration
(V̂ 0.6566 V, µ̂ 0.541, k = 1.85: reset 554 µs, T₁ 314 µs). The 20 subset samples in subset order as one chain, 1 s off
between, step 0 from the calibration start state. Compared with the C3 independent runs of the same cell (each from the
calibration start state).

| Chain | Correct / valid of 20 | Same outcome as independent | Race shift vs independent | Rail at end of reset |
|---|---|---|---|---|
| Independent (C3 cell) | 15 / 20 | — | — | 0.344 V |
| **v2 chain** (reset 300·k = 554 µs) | **15 / 20** | **20 / 20** | +0.004…+0.012 µs | 0.3444 V on every step |
| v2 chain with the **v1 reset length** (300 µs) | 15 / 20 | 20 / 20 | −0.46…−0.51 µs | 0.3442 V on every step |

- **No history dependence is left at µ ×0.5 under v2.** Every step starts from the same 1 s-off rail level (0.265 V;
  higher than at µ ×1, 0.231 V, because the slower devices discharge less) whatever the previous winner.
- **The reset length does not matter here any more.** The energy/host study found that the 300 µs reset does not finish at µ ×0.5
  (rails ended reset at 1.04 V instead of 0.90 V, coming down from ≈ 3.2 V in the warm start). Under power gating the
  rails start *below* the reset floor, so the reset has nothing to pull down; the 254 µs longer reset only lets the
  rails creep up 0.2 mV more and changes the race by 0.5 µs. Its cost is ≈ 76 nJ per classification (254 µs at
  the C1 mean reset-phase power of 299 µW; an estimate, these runs were not instrumented).
- What C5 does not show: the v1 history effect itself at µ ×0.5 (a warm-start chain under v1) was not run; the
  comparison is against v2's own independent runs.

## 8. C6: the lower |V_th| edge (120 runs, + C6b 60 runs, + short-run diagnostic)
Sources: [c6_lower_edge.json](summary/c6_lower_edge.json), [c6_diag.json](summary/c6_diag.json), runs `raw/C6/`,
`raw/C6diag/`. µ ×1, each |V_th| with its own calibration session; 20-sample subset. 0.57–0.61 V is the H5 extension
(declared after the C6 calibration races showed stuck latches at every grid point of the campaign specification).

| \|V_th\| (V) | V̂ err (mV) / µ̂ / k / flag | V₁/V₂ (V) | **v2** correct / valid | median race (µs) | median highest losing `na` at read (V) |
|---|---|---|---|---|---|
| 0.45 | +4.6 / 1.017 / 1.00 / True | [2.015, 2.595] | 0 / 0 (stuck_latched 20) | None | 3.216 |
| 0.47 | +4.1 / 1.015 / 1.00 / True | [1.996, 2.576] | 0 / 0 (stuck_latched 20) | None | 3.213 |
| 0.49 | +3.6 / 1.013 / 1.00 / True | [1.976, 2.556] | 0 / 0 (stuck_latched 20) | None | 3.212 |
| 0.51 | +3.0 / 1.011 / 1.00 / True | [1.957, 2.537] | 0 / 0 (stuck_latched 20) | None | 3.21 |
| 0.53 | +2.5 / 1.009 / 1.00 / True | [1.937, 2.517] | 0 / 0 (stuck_latched 20) | None | 3.21 |
| 0.55 | +1.8 / 1.005 / 1.00 / True | [1.918, 2.498] | 0 / 0 (stuck_latched 20) | None | 3.21 |
| 0.57 | +1.9 / 1.001 / 1.00 / False | [1.898, 2.478] | 0 / 0 (none_latched 20) | 1677.9 | 1.809 |
| 0.59 | +4.0 / 1.024 / 1.00 / False | [1.876, 2.456] | 15 / 20 | 1655.9 | 1.479 |
| 0.61 | -3.6 / 1.006 / 1.00 / False | [1.864, 2.444] | 15 / 20 | 1754.0 | 1.276 |

| v1 reference | correct / valid |
|---|---|
| 0.45 fixed (fitc10 3A) | 0 / 0 (stuck_latched 20) |
| 0.55 fixed (fitc10 3A) | 14 / 19 (multi_latched 1) |
| 0.50 rstb50 (energy/host study E11.1) | 13 / 17 (none_latched 3) |
| 0.65 rstb50 (energy/host study E11.1) | 15 / 20 |


**Result: under v2 the lower edge moves UP, from 0.541 V (v1, fixed levels) to between 0.57 and 0.59 V.** At
0.45–0.55 V all five latches regenerate high at the end of reset in every run (`stuck_latched` 120/120; the host sees all
five outputs high at the start of trip counting). At 0.57 V every run ends `none_latched`. At 0.59 and 0.61 V the die
classifies at the nominal rate (15/20). The energy/host study's host fix (`rstb` at 50 µs, warm start) gave 13/20 at 0.50 V and moved
the short-run edge to 0.477 V; **combined with power gating it no longer works.** The a1 calibration itself is fine down
to 0.45 V (|V_th| error +1.8…+4.6 mV); the race cross-check flags 0.45–0.55 V (no race finishes).

**Mechanism (short-run diagnostic, #81, fixed levels; `na` = highest latch node at 320 µs):**

| Start state / `rstb` release | stuck for \|V_th\| ≤ | works from | `ref` at 311 µs (0.65 V) | `d1` at 311 µs (0.65 V) | `na` at 320 µs (0.65 V) |
|---|---|---|---|---|---|
| v1 warm, `rstb` 150 (energy/host study) | 0.541 V | 0.542 V | 1.38 V | — | 1.11 V |
| v1 warm, `rstb` 50 (energy/host study) | 0.477 V | 0.478 V | 1.56 V | 3.00 V | 0.93 V |
| **v2: 1 s-off start, `rstb` 50** | **0.59 V** | **0.60 V** | 1.17 V | 2.85 V | 1.39 V |
| 1 s-off start, `rstb` 150 | 0.60 V | 0.61 V | — | — | — |
| all-zero start, `rstb` 50 or 150 | ≥ 0.67 V (criterion) | — | 1.05 V | 2.80 V | 1.79 V |

1. The stuck mechanism is the energy/host study's: after `rstb` releases, each `na` can only fall through the weak X84 load against
   the trip driver X83, whose "off" gate sits at the comparator output `d` ≈ `vls`; if `na` is still above 1.65 V when
   `rstr` releases, the latch regenerates high.
2. **Power gating removes the residual `ref` charge** the warm start carried. After 1 s off `ref` starts at 0.15 V, the
   `ref` reset (X69, during `rstb` low) can only pull it *down*, so it ends sampling at 1.17 V instead of 1.38–1.56 V.
   `vls` and `d` are ≈ 0.12–0.15 V lower, X83 conducts more, `na` decays more slowly (1.39 V at 320 µs at nominal, a
   0.26 V margin to 1.65 V against 0.54 V in v1), and the edge moves up. Releasing `rstb` earlier now helps by only
   10 mV (its benefit came from stopping the `ref` reset early, which does nothing when `ref` starts low).
3. **The early-end rule then turns a slow decay into a failure.** At 0.57–0.61 V `na` is still above 1.65 V for 2–27 µs
   after counting starts (320 + e µs). The integrating host timer (H4.2) counts that time: at 0.57 V (26.6 µs counted) the
   rows go off ≈ 23 µs after the real trip, before the latch completes (`none_latched` 20/20); at 0.59 V (13 µs counted)
   and 0.61 V (2 µs) the latch still finishes. **A literal "first output" host would abort every run at 0.59 and 0.61 V.**
4. The all-zero start (energy/host study O2/O12) is worse on this criterion (na 1.79 V at 320 µs at 0.65 V); it classified at
   0.65 V only because O2 had no early end and O12 used the same integrating timer (in this study's all-zero dev run
   of #81, `raw/dev/dev_s81_nom`, the timer counted ≈ 10 µs before the real trip; O12's own count was not extracted).

## 9. v1 vs v2 (all phases)
| Condition (N) | v1 | **v2** | Source |
|---|---|---|---|
| Nominal, 90 test samples | 62/90, valid 87 | **62/90, valid 87; 90/90 outcomes identical** (McNemar p = 1.0) | C1 |
| Energy per classification | 714 nJ (VDD on: + 98–199 µW standby) | **588 nJ, standby 0** | C1 |
| Back-to-back chain, 10 | 10/10 same; trip shift ≤ 4.1 µs | 10/10 same; trip shift ≤ 0.003 µs | C1 |
| Stress, 5 runs | 0/134 > 3.5 V; worst 3.34 V; crossbar 2.43 V | 0/134 > 3.5 V; worst 3.30 V; **crossbar 3.03 V; nodes to −2.2 V** | C2 |
| µ ×0.7 / ×0.5 at 0.65 V (20) | 13 / 8 | **15 / 15** | C3 vs B4 |
| ΔV_th +0.2 V, µ ×1 / ×0.7 / ×0.5 (20) | 0 / 0 / 0 (no re-trim); 14 / 13 / 13 (ideal re-trim) | **14 / 14 / 15 (learned)** | C3 vs B4 |
| ΔV_th +0.35 V, µ ×1 / ×0.7 / ×0.5 (20) | 0 / 0 / 0; 12 / 13 / 13 (ideal) | **13 / 13 / 13 (learned)** | C3 vs B4 |
| 25-cell aging grid (500) | not run (9 of 25 cells; none/ideal) | **351/500, every cell 13–15/20** | C3 |
| History at µ ×0.5, 20-chain | rails end reset at 1.04 V, start depends on history (B4 §5.1, not chained) | 20/20 identical to independent runs | C5 |
| Mismatch, 3B-V anchor 20 mV (100) | 64/100, valid 95 | **64/100, valid 97; 94/100 outcomes identical** (p = 1.0) | C4 |
| Lower edge | works from 0.542 V (fixed); 13/20 at 0.50 V with `rstb` 50 | **fails at ≤ 0.57 V; works from 0.59 V** | C6 |

## 10. What this does not show
- **Not measured hardware.** Simulation only; `fitc10` is a reconstructed corner (C10-DNTT on Si, currents read by eye);
  JOFF and LOV are not fitted; the Variant 3 sizing is rebuilt from the author's decisions.
- **The host is ideal:** noise-free I_DD meter and timer, ideal line drivers, 1 mV level resolution, instantaneous
  logic. Meter resolution, noise and offset would add to the a1 error (§5 shows the noise-free error only).
- **Design-time constants come from the same compact model** they are applied to (c_a1, I_ref, c_race on the nominal
  die). Model error between the host's correction and a real device is not represented, and it is the main risk for
  a1: under cold start its offset moved by 19 mV with the start state alone.
- **The µ estimator was chosen on development corners that overlap the C3 grid** (H1-outcome 3; 4 candidates, no
  fitted constant beyond the nominal-die values). C3's estimate errors are therefore not a fully independent test.
- **C1 cannot show estimate error:** the nominal die is the design-time die.
- **Aging inputs are proxies,** applied as uniform global shifts with no mismatch growth, no per-device drift, no R_C
  change, no time dependence; µ above ×1 was not tested.
- **Power gating:** the VDD-off time is exactly 1 s everywhere. Other idle lengths change the start state (rails
  0.62 V after 1 ms, 0.11 V after 10 s) and therefore the race time and the lower edge; they were not evaluated. The
  10 µs power-down ramp drives internal nodes to −2.2 V; slower or sequenced power-down was not tried. Energy returned
  during the power-down is not credited and host electronics are not counted.
- **Calibration:** one calibration session per die/condition, always from an all-zero start; its energy (≈ 3 µJ) is
  partly estimated (races not instrumented). How often a real host must re-calibrate is not studied.
- **Lower edge:** 20 samples per point; the v2 edge (0.57–0.59 V) is bracketed by two 20-sample points, not bisected;
  the mechanism comes from short runs on one sample. The diagnostic is post-freeze analysis, not a protocol test.
- **Mismatch:** one anchor (20 mV), 5 dies, V_th only (µ and R_C nominal).
- **Weights:** results apply to `F_hw_m4_firstpass.npy` only. N = 20 per cell: one sample is 5 points.

## 11. Proposals (separate from the results; none simulated unless stated)
1. **Fix the v2 lower edge on the host side:** start the output watch at the start of C2 (or require an upward
   crossing of 1.65 V) instead of a level check from 320 + e µs, so a slowly decaying `na` is not counted as an output.
   This addresses mechanism 3 of §8 (0.57–0.61 V) but not the stuck latches at ≤ 0.55 V, which come from the low `ref`
   after power gating (mechanism 2). Candidate for the latter, host-only: a longer `rstb`-low precharge plus a
   longer post-`rstb` decay window, or a brief calibration-level sampling step before the `na` decay window to charge
   `ref` (the energy/host study's "lower Vcal" did not help in the warm case). Not simulated.
2. **Circuit fix for the lower edge** (energy/host study §8 item 5, now more important): drive `d` to VDD when idle, a stronger
   `na` reset device, or a shorter-L X84; any of them removes the dependence on `ref`'s start level. Needs a stress audit.
3. **Replace or recalibrate the race-timing cross-check:** it reads +26…+67 mV high at 0.95–1.00 V and gave the only
   flag in C3 (a false alarm). Options: |V_th|-dependent design-time offsets (from more nominal-model corners), a wider
   flag band that grows with V̂, or a cross-check on µ̂ (race time × µ̂ should be ≈ constant at fixed overdrive).
4. **Correct µ̂'s bias** (+0…+12 %, R_C does not scale with µ): a one-parameter design-time correction from two model
   corners; not needed for accuracy in C3, but it would give k closer to 1/µ.
5. **Slower or sequenced power-down** (e.g. rows and `rstb` down before VDD, or a 100 µs ramp) to limit the −2.2 V
   node excursions found in C2; check with the stress audit.
6. **Idle-time dependence:** repeat C1 (subset) and the lower edge at T_off = 1 ms, 100 ms and 10 s; the start state
   (rails 0.11–0.62 V) moves the race time and probably the edge.
7. **Drop the reset extension for µ compensation** (C5: no effect under power gating, ≈ 76 nJ per classification at
   µ ×0.5, estimated); keep T₁, D and the window scaled. Would need its own aging-grid check.
