# Tortoise wrap-up studies: optional studies

**Status: complete (2026-10-31 ≈ 04:00 UTC).** Protocols: [DECISIONS.md](DECISIONS.md) (E0, S1–S4), each committed before its
first evaluation run. Simulation only (ngspice-42, reconstructed `fitc10` corner,
synthetic data). Tortoise v1.0 is unchanged; every circuit change below is a named **candidate** variant.

## Summary
- **Study 1 (mode W robustness):** succeeds. Mode W at |V_th| 0.55 V classifies 15/20 at µ ×1, ×0.7 and ×0.5; drift of
  +0.10/+0.20 V switches the die to mode G on re-calibration (6/6 cells), 15/20 each; mismatch at 0.55 V (5 dies)
  **65/100** (55.3–73.6 %) vs v2's 64/100, paired p = 1.0.
- **Study 2 (0.49 V edge):** succeeds. Mechanism (20/20 samples): at 0.49 V the lock-out is half on before any class
  wins. **candidate-edgeA** (X80 L 120 → 20 µm, 134 TFTs) classifies 15/20 at 0.47, 0.49 and 0.51 V (Tortoise v1.0: 0/20 at
  0.49 V) and 0/20 at 0.45 V; nominal outcomes identical on 90/90; 0/134 above 3.5 V. candidate-edgeB (P_k L 5 → 10 µm)
  also 15/20 at 0.49 V.
- **Study 3 (bias row, candidate-bias, candidate):** frozen choice (138 TFTs) on the test set once: **63/90 = 70.0 %**
  (59.9–78.5 %) vs Tortoise v1.0 62/90, paired 9 gained / 8 lost, McNemar p = 1.0 → **no resolvable change**; validity
  85/90; mismatch (3 dies) 40/60 = Tortoise v1.0's 40/60; stress 0/138 above 3.5 V; yield ×0.922 for +4 TFTs.
- **Study 4 (prior art, MCU):** complete (§4). An MCU does the whole job for ≈ 0.42 µJ (0.26–1.03 µJ); Tortoise's die
  alone needs 0.59 µJ and, with the host it needs anyway, ≥ 1.79 µJ. Tortoise loses in this architecture.

## 1. Study 1: mode W robustness (Tortoise v1.0, host protocol v2.1 unchanged)
Protocol: DECISIONS S1 (+ S1-D1: no standby idles on the remaining mismatch dies). Runner `scripts/s1_modew.py`, summary
`scripts/s1_summary.py` → [summary/s1_modew.json](summary/s1_modew.json), [summary/s1_tables.md](summary/s1_tables.md),
identity check [summary/s1_identity.json](summary/s1_identity.json). Each cell is its own v2.1 calibration session (the
host re-calibrates after drift and re-decides the mode); 20-sample subset; independent runs.

| \|V_th\| (ΔV_th from 0.55 V) | µ | mode (V̂, error) | µ̂ (error), k | correct / valid of 20 (Wilson 95 %) | failures | race median (µs) | source | v2 reference (base 0.65 V + ΔV_th): correct / valid |
|---|---|---|---|---|---|---|---|---|
| 0.55 V (+0.00) | ×1 | W (0.5518 V, +1.8 mV) | 1.005 (+0.5 %), 1.000 | **15 / 20** (53.1–88.8 %) | — | 1269.4 | reused (identical netlists) | C3 0.65 V x1.0: 15 / 20 |
| 0.55 V (+0.00) | ×0.7 | W (0.5609 V, +10.9 mV) | 0.744 (+6.3 %), 1.344 | **15 / 20** (53.1–88.8 %) | — | 1835.8 | simulated | C3 0.65 V x0.7: 15 / 20 |
| 0.55 V (+0.00) | ×0.5 | W (0.5563 V, +6.3 mV) | 0.551 (+10.3 %), 1.813 | **15 / 20** (53.1–88.8 %) | — | 2844.4 | simulated | C3 0.65 V x0.5: 15 / 20 |
| 0.65 V (+0.10) | ×1 | G (0.6500 V, +0.0 mV) | 1.000 (+0.0 %), 1.000 | **15 / 20** (53.1–88.8 %) | — | 1636.5 | reused (identical netlists) | C3 0.75 V x1.0: 15 / 20 |
| 0.65 V (+0.10) | ×0.7 | G (0.6557 V, +5.7 mV) | 0.734 (+4.9 %), 1.362 | **15 / 20** (53.1–88.8 %) | — | 2269.5 | reused (identical netlists) | C3 0.75 V x0.7: 15 / 20 |
| 0.65 V (+0.10) | ×0.5 | G (0.6566 V, +6.6 mV) | 0.541 (+8.1 %), 1.849 | **15 / 20** (53.1–88.8 %) | — | 3150.9 | reused (identical netlists) | C3 0.75 V x0.5: 15 / 20 |
| 0.75 V (+0.20) | ×1 | G (0.7490 V, -1.0 mV) | 0.997 (-0.3 %), 1.003 | **15 / 20** (53.1–88.8 %) | — | 1460.9 | reused (identical netlists) | C3 0.85 V x1.0: 14 / 19 |
| 0.75 V (+0.20) | ×0.7 | G (0.7532 V, +3.2 mV) | 0.731 (+4.4 %), 1.368 | **15 / 20** (53.1–88.8 %) | — | 2058.1 | reused (identical netlists) | C3 0.85 V x0.7: 14 / 19 |
| 0.75 V (+0.20) | ×0.5 | G (0.7519 V, +1.9 mV) | 0.536 (+7.3 %), 1.864 | **15 / 20** (53.1–88.8 %) | — | 2898.7 | reused (identical netlists) | C3 0.85 V x0.5: 15 / 20 |

| Die | mode (V̂) | correct / valid of 20 | C4 (v2, same die at 0.65 V) correct / valid |
|---|---|---|---|
| die1 | W (0.5544 V) | 13 / 20 | 12 / 19 |
| die2 | W (0.5536 V) | 13 / 19 | 13 / 19 |
| die3 | W (0.5541 V) | 15 / 20 | 15 / 20 |
| die4 | W (0.5511 V) | 11 / 19 | 11 / 19 |
| die5 | W (0.5513 V) | 13 / 20 | 13 / 20 |
| **pooled** | | **65 / 98** of 100 (55.3–73.6 %) | 64 / 97; paired S1-only 1 / C4-only 0, McNemar p = 1.0 |

**Reused cells (S1.3).** Seven cells' calibrations were identical to existing ones (0.55 V × µ1 = host_v21 E1; the six
drifted cells = host_v2 C3): all 7 × 20 classification netlists were rebuilt and are byte-identical to the stored ones
(140/140), and the 2 re-simulated samples per cell reproduced the stored outcomes and times exactly (14/14, 0.000 µs).

**Reading.**
- **Mode W under mobility loss works:** at |V_th| 0.55 V the die stays in mode W at µ ×1, ×0.7 and ×0.5 and classifies
  15/20 at each (all valid), the same as v2's mode G at 0.65 V with the same µ. The host's estimates were further off
  than in v2's grid: V̂ +10.9 mV at µ ×0.7 (v2 range −4.4 … +8.5 mV, H2-07) and µ̂ +10.3 % at µ ×0.5; this cost nothing.
- **The mode switch happens as designed:** every drifted cell (|V_th| 0.65 and 0.75 V, all three µ) re-calibrated to
  mode G (V̂ 0.650–0.753 V, all ≥ 0.600 V) and is then v2 exactly, 15/20 everywhere. A die that drifts from 0.55 V
  therefore leaves mode W (and its standby) at the next re-calibration.
- **Standby of the mode-W cells** (median over the 1 s idle): 183.1 / 146.4 / 116.4 µW at µ ×1 / ×0.7 / ×0.5 (lower
  mobility, lower static current). Classification energy (median): 434 / 483 / 558 nJ (longer races at larger k).
- **Mismatch at 0.55 V (5 C4 dies, 20 mV anchor): 65/100 (55.3–73.6 %), valid 98/100**, against v2's 64/100 on the same
  dies at 0.65 V; paired per (die, sample): 1 gained, 0 lost, exact McNemar p = 1.0 → matches v2. Every die ran mode W
  (V̂ 0.551–0.554 V). Per die the results equal C4's within one sample.
- **Study 1 succeeds** by its pre-declared reading (every cell works, mismatch matches v2).

**What this does not show.** Global corners and one assumed mismatch model; 20 samples per cell (one sample = 5
points). The combination of mismatch with drift, mode W at other base |V_th| than 0.55 V, and mode W chains under µ
loss were not run. The secondary forced-W cells (S1-F) were **not run** (budget). Standby under mismatch is not reported
(S1-D1; on dies 1, 2 and 4 the idle needed the solver fallback). The host is ideal (noise-free I_DD meter).

## 2. Study 2: the 0.49 V edge
### 2.1 Mechanism (stored node voltages, no new simulation; `scripts/s2_mechanism.py` → [summary/s2_mechanism.md](summary/s2_mechanism.md))
All 20 subset samples at each |V_th| (host_v21 E1 runs, mode W at 0.49–0.55 V; v2.1 mode G at 0.61 V; host_v2 C3 at
0.65 V). Median (range) over the 20 samples, V:

| \|V_th\| (V) | correct / 20 | `win` 100 µs into C2 | `lockb` | lock-device V_SG (= 3.3 − `lockb`) | lowest `d` of the leading class | leading `na` max |
|---|---|---|---|---|---|---|
| 0.49 | 0 (16 timeout, 4 none_latched) | 2.445 | 2.228 | **1.072** (> \|V_th\|: on) | 2.834 | 1.584 (1.508–1.664) |
| 0.51 | 15 | 2.068 | 2.888 | 0.412 (< \|V_th\|: off) | 2.668 | 3.205 |
| 0.53 | 15 | 1.763 | 2.932 | 0.368 | 2.637 | 3.206 |
| 0.55 | 15 | 1.533 | 2.950 | 0.350 | 2.611 | 3.207 |
| 0.61 | 15 | 1.202 | 2.973 | 0.327 | 2.581 | 3.207 |
| 0.65 | 15 | 1.113 | 2.982 | 0.318 | 2.524 | 3.212 |

**Reading.** The shared node `win` should idle low until a class latches. Its idle level is a balance between the five
P_k pull-ups (gates at `nb` ≈ 2.87 V, V_SG ≈ 0.43 V, i.e. subthreshold leakage that grows exponentially as |V_th|
falls) and the weak idle pull-down X80 (5/120 µm after Variant 3's ×6 lengthening). Between 0.51 and 0.49 V that level
crosses the switching point of the `lockb` inverter: at 0.49 V `lockb` sits at 2.23 V on every sample, the lock
devices (gate `lockb`, source VDD) see V_SG ≈ 1.07 V and are on **before any class has won**, and they hold every
comparator output `d` high. The leading class's `d` then falls only to ≈ 2.83 V, its trip driver gets ≤ 0.48 V of gate
drive, and its `na` peaks at 1.5–1.66 V: no regeneration (timeouts), or a brief crossing of 1.65 V that is not latched
at the read (`none_latched`). This refines the v2.1 report's "comparator/latch swing too weak": the swing is weak
because the lock-out is already half engaged. Monotone in |V_th| on all 20 samples of every point.

### 2.2 Development screen (training sample #123; development, not a result)
Disclosed in DECISIONS S2.0 ([summary/s2_dev.json](summary/s2_dev.json)): X80 L 60 µm, X80 L 20 µm and P_k L 10 µm each
gave the right class at 0.49 V and `none_latched` at 0.45 V (lock off, regeneration too slow for the early-end window);
XI2 L 60 µm failed at 0.49 V; X80 L 20 + wider trip drivers stuck all latches at 0.45 V. Variants chosen:
**candidate-edgeA** (X80 L 120 → 20 µm) and **candidate-edgeB** (P_k L 5 → 10 µm), both 134 TFTs.

### 2.3 Variant runs (DECISIONS S2.1–S2.3 with S2-D1, S2-D2)
Runner `scripts/s2_runs.py` (drivers `s2_chain.sh` → `s2_chain2.sh` → `s2_tail.sh`, same runs, reordered after the
restarts), summary `scripts/s2_summary.py` → [summary/s2_edge.json](summary/s2_edge.json),
[summary/s2_tables.md](summary/s2_tables.md); stress [summary/s2_stress_R10.2-edgeA.json](summary/s2_stress_R10.2-edgeA.json).
v2.1 unchanged; each point its own calibration session (the mode is whatever V̂ decides); 20-sample subset.

| \|V_th\| (V) | Tortoise v1.0 (v2.1) correct / valid | candidate-edgeA: mode, correct / valid (Wilson 95 %), failures | candidate-edgeB: mode, correct / valid (Wilson 95 %), failures |
|---|---|---|---|
| 0.45 | not run | W, **0 / 0** (0.0–16.1 %), none_latched 20 | not run | 
| 0.47 | not run | W, **15 / 20** (53.1–88.8 %), — | not run | 
| 0.49 | 0 / 0 | W, **15 / 20** (53.1–88.8 %), — | W, **15 / 20** (53.1–88.8 %), — | 
| 0.51 | 15 / 20 | W, **15 / 20** (53.1–88.8 %), — | W, **15 / 20** (53.1–88.8 %), — | 
| 0.65 | 15 / 20 | G, **15 / 20** (53.1–88.8 %), — | G, **15 / 20** (53.1–88.8 %), — | 

- candidate-edgeA: nominal check **pass**; lower edge 0.47 V; X80 (idle pull-down of win) L 120 -> 20 um, W 5 um.
- candidate-edgeB: nominal check **pass**; lower edge 0.49 V; P_k pull-ups X90/X100/X110/X120/X130 L 5 -> 10 um, W 80 um.

- **Nominal check (0.65 V): both variants pass**, 20/20 per-sample outcomes identical to Tortoise v1.0.
- **0.49 V: both variants 15/20, all valid** (Tortoise v1.0: 0/20), and the 20 outcomes equal the nominal die's on 20/20
  samples; 0.51 V: 15/20 for both. Phase-2 choice (S2-D2): tie 30/30 → candidate-edgeA.
- **candidate-edgeA at 0.47 V: 15/20; at 0.45 V: 0/20** (20 `none_latched`: the lock stays off, but the latch regenerates
  too slowly for the early-end window, as in the development screen). Its lower edge moves from **between 0.49 and
  0.51 V (Tortoise v1.0) to between 0.45 and 0.47 V**; candidate-edgeB's 0.47/0.45 V points were not run (S2-D2), so its edge
  is only known to be ≤ 0.49 V.
- **candidate-edgeA, all 90 test samples at the nominal die (S2-D1): 62/90, valid 87/90, outcomes identical to Tortoise v1.0
  on 90/90** (paired 0 / 0); median energy 588.7 nJ (source-current method; Tortoise v1.0 H2-02: 587.9 nJ, instrumented).
- **candidate-edgeA stress audit** (C2 procedure, 1× ramps, 5 runs incl. power-up/down): **0 of 134 above 3.5 V**; worst
  XNP1 3.300 V; crossbar max 3.033 V; most negative node −2.18 V (power-down); Tortoise v1.0 (H2-05): worst 3.300 V, −2.20 V.
- **Cost:** no device added (134 TFTs); X80 is 6× stronger, so a1's supply current changes: the variant needs its own
  design constants (a1 offset −47.8 vs −50.9 mV, I_ref 31.73 vs 31.44 µA). Mode-W standby 196–207 µW at 0.47–0.51 V
  (Tortoise v1.0: 192.1 µW at 0.51 V; 209.2 µW at 0.49 V) and classification energy 476–505 nJ.
- **Study 2 succeeds** by its pre-declared reading: the best variant (edgeA) passes the nominal check, works at 0.49 V,
  keeps 90/90 nominal outcomes and has 0 TFTs above 3.5 V. It is a **candidate (candidate-edgeA)**, not part of Tortoise v1.0.

### 2.4 What this does not show
20 samples per point, µ ×1, no mismatch, global corners; edgeB's 0.47/0.45 V points not run; the 0.45 V failure
(slow regeneration) is not addressed by either variant. Neither variant was run with µ loss, drift, mismatch or in a
mode-W chain, nor through the 1–100 µs ramp-rate stress set. The mechanism analysis is from waveforms of Tortoise v1.0
runs; the variants' own waveforms were stored (not included in this release) but were not analysed beyond the outcomes. The dev screen that chose
the variants used one training sample.

## 3. Study 3: bias-row variant candidate-bias (`R10.2-bias`; candidate, not Tortoise v1.0)
Protocol: DECISIONS S3 with S3-D1 (20 S samples per finalist) and S3-D2 (3 mismatch dies). Scripts:
`scripts/s3_variant.py` (builder), `s3_train.py` (surrogate + training), `s3_runs.py` (SPICE), `s3_chain.py`,
`s3_summary.py`. Summaries: [s3_surrogate_params.json](summary/s3_surrogate_params.json), [s3_cv.json](summary/s3_cv.json),
[s3_select.json](summary/s3_select.json), [s3_eval.json](summary/s3_eval.json),
[s3_stress_S3_le60_m30_b138.json](summary/s3_stress_S3_le60_m30_b138.json), [s3_nobias_cv.json](summary/s3_nobias_cv.json).

### 3.1 Design
A host-driven 7th row `row7` with one 54 µm-long bank per class (F_b fingers of 10 µm), driven at V₁ from the start of C1
for WMIN + 0.5·T₁·k (105 µs at k = 1), off in calibration, sampling and C2. Host lines: 11 instead of 10. TFTs: 113 +
input banks + bias banks.

### 3.2 Surrogate recalibration (40 K training samples, probe matrix F_b = [4, 3, 11, 10, 0], v2.1 nominal)
| Quantity | Value |
|---|---|
| Common rail start level R (v2.1 cold start) | 0.355 V (the weight-retraining study, v1 warm start: 0.895–0.899 V per class) |
| α (rail V per input finger·µs), α_b/α | 9.996·10⁻⁵ V, **0.983** |
| rms residual of the 200 rail voltages at C2 start | **0.12 mV** |
| Effective trip level Θ_k | 2.131–2.133 V (v1: 2.208–2.211 V) |
| In-sample agreement (40 runs): winner / validity / outcome | **40/40 / 40/40 / 40/40** (acceptance ≥ 36/40: passed) |

### 3.3 CV and selection (training data only)
16 configs × 20 group splits of T; score S3 = 0.5·A_nom + 0.5·A_mm (surrogate accuracy on the validation folds, nominal
and over 500 analytic mismatch dies). Best configs (mean over splits; SD of S3 over splits ≈ 5 points):

| Config | S3 | A_nom | A_mm | TFTs (median) |
|---|---|---|---|---|
| **le60, m = 30 µs, b138** (best b138) | 66.4 % | 70.3 % | 62.5 % | 138 |
| eq60, m = 30 µs, b138 | 65.7 % | 69.2 % | 62.1 % | 138 |
| **le60, m = 30 µs, b134** (best b134) | 65.2 % | 68.3 % | 62.1 % | 134 |

**Post-hoc (disclosed; training data only, not used for any selection):** the same config with the bias row forced empty
(the Tortoise v1.0 crossbar form), same recalibrated surrogate and splits: A_nom 68.2 % against 70.3 % with the bias row,
paired difference **+2.2 points (SD 4.9 over 20 splits; better on 11, equal on 5, worse on 4)**. The bias row is worth
about 2 points in CV here, less than the ≈ 6 points of the float ceilings (WS-01 vs WS-02).

**SPICE on 20 held-out S samples (S3-D1):** b138 finalist **14/20** (valid 20/20), b134 finalist 12/20 (valid 19/20,
one double latch). Winner: **b138** — F_b = [4, 4, 12, 10, 0], column sums [60, 60, 59, 60, 60], 21 input + 4 bias
banks, **138 TFTs**. For reference only (v1 protocol, not paired): Tortoise v1.0's weights scored 13/20 on the same 20
samples in the weight-retraining study. Frozen with SHA-256 and committed (`1fa79be`, 22:22 UTC) before any test-set run. The variant
uses its own design constants (its a1 offset/I_ref differ from Tortoise v1.0's by more than the S2.2.1 tolerance because
one column has 59 fingers).

### 3.4 Evaluation of the frozen choice
| Measure | candidate-bias (frozen) | Tortoise v1.0 (H2-01, C4, C2) |
|---|---|---|
| **Test set (90, run once)** | **63/90 = 70.0 %** (59.9–78.5 %) | 62/90 = 68.9 % (58.7–77.5 %) |
| Paired per test sample | 9 gained, 8 lost, exact McNemar **p = 1.0** → **no resolvable change** | — |
| Validity | 85/90 (87.6–97.6 %), 5 double latches | 87/90, 3 double latches |
| Size-scaled V_th mismatch, 20 mV, dies 1–3 × subset (N = 60) | 40/60 (54.1–77.3 %), valid 58/60 | 40/60 on the same dies (C4); paired 9 / 9, p = 1.0 |
| Stress audit, 5 runs incl. power-up/down at 1× | **0 of 138 above 3.5 V**; worst XNP1 3.300 V; crossbar max 3.034 V (bias bank XB4); nodes to −2.20 V | 0 of 134; worst 3.300 V; crossbar 3.033 V |
| Energy per classification (median) | 575 nJ (row7 driver 0.09 nJ) | 588 nJ (H2-02) |
| TFTs; yield model 0.98^N | 138; 0.0615 | 134; 0.0667 → **×0.922 (−7.8 %)** for +4 TFTs |

Per class on the test set the bias moved accuracy toward class 4 (13 of 18 correct, Tortoise v1.0: 8) and away from class 3
(4 of 18, Tortoise v1.0: 5); with N = 18 per class none of this is resolvable.

**Reading.** A +1.1-point test difference (+1 sample) for +4 TFTs, a ≈ 8 % lower yield under the 0.98^N model, one more
host line, and slightly lower validity. On this evidence the bias row does **not** show a measurable benefit; the
≈ 2-point CV gain (post-hoc) is below what N = 90 can resolve (Wilson half-width ≈ 9–10 points). candidate-bias is a
candidate that works (no stress or energy penalty in simulation) but is not shown to be better.

### 3.5 What this does not show
The bias gain could be real but small; testing it would need far more test samples than 90. The surrogate was
recalibrated on 40 runs of one probe matrix at the nominal die; its mismatch paths are the weight-retraining study's (v1-calibrated),
with the reset term switched off for v2.1. Finalists were compared on 20 S samples (S3-D1), which can only detect large
differences; the old-weights reference on S is a v1-protocol number, not paired. Mismatch: 3 dies (S3-D2), assumed
model. Re-trimmed |V_th|, µ loss and mode W were not run for the variant. The yield model is a textbook independent-
defect model with an assumed 2 % per-device loss, not a process number.

## 4. Study 4: prior art and the microcontroller question
Full text, tables and citations: [prior_art/PRIOR_ART.md](prior_art/PRIOR_ART.md); every cited work confirmed by a
logged Crossref / Semantic Scholar lookup with its DOI (abstract-level claims only), request log
[LOG.jsonl](prior_art/lookups/LOG.jsonl) (the saved third-party responses are not redistributed); MCU arithmetic in
[scripts/s4_mcu.py](scripts/s4_mcu.py) → [summary/s4_mcu.json](summary/s4_mcu.json) (index rows WU-40 to WU-43).

### 4.1 Prior art (26 works confirmed, five groups)
Closest work per group: printed bespoke and analog ML classifiers and printed neuromorphic circuits with
hardware-aware training (Mubarik 2020, Weller 2021, Zhao 2022, Armeniakos 2022–2024); a hardwired ML engine and a
32-bit processor in flexible metal-oxide TFTs (Ozer 2020, Biggs 2021); an organic microprocessor on foil (Myny 2012);
organic electrochemical synapses and neurons (van de Burgt 2017, Harikesh 2022); race logic and race-tree classifiers
(Madhavan 2014, Tzimpragos 2019/2021); time-domain VMM and PWM weighted sums (Bavandpour 2019, Yamaguchi 2021); VMM +
winner-take-all analog classifiers (Ramakrishnan & Hasler 2014); a simulated TFT winner-take-all (Ramya 2021);
temporal-coding learning (Mostafa 2018); unipolar organic ADC/DAC and the pseudo-CMOS style (Marien 2011, Zaki 2012,
Huang 2011); wound dressings with sensors and a microcontroller or off-patch AI (Mostafalu 2018, Pang 2020, Kalasin
2022, Shirzaei Sani 2023).

**Novelty statement.** Not new: racing signals to compute, integrating time-encoded inputs on a capacitor,
winner-take-all linear classification, classifiers for printed/flexible electronics, unipolar organic analog
circuits, and sensor-laden wound dressings — each has published precedents found here. Possibly new (not found in
this search): an "integrate, then race" linear classifier with a latch lock-out in a single-gate p-type-only OTFT
circuit at 3.3 V without a negative supply, combined with a host that learns |V_th| and µ from its own supply current.
Unclear: whether that combination exists in work the search did not reach, and whether it has value in hardware.

### 4.2 The microcontroller comparison (datasheet typicals, 25 °C; arithmetic, not measurement)
| | MSP430FR2433 | MSPM0L1306 | Tortoise v1.0 (simulated) |
|---|---|---|---|
| Energy per classification: wake-up + 6 ADC conversions + 6 × 5 classifier | **0.42 µJ** (0.26–1.03 µJ for 500–3000 assumed cycles) | 0.41 µJ | die 0.59 µJ (H2-02) + host ≥ 1.09 µJ idling for the 2194 µs median read time + ADC/wake 0.11 µJ = **≥ 1.79 µJ** (≈ 4.3×) |
| Standby | 2.94 µW (LPM3), 0.048 µW (LPM4.5) | 3.3 µW (standby) | 0 on the die (mode G); the host's own standby as left |
| Size | 2.29 × 2.34 mm package (5.36 mm²) | 3 × 2 mm package | ≥ 1.89 mm² active (0.30 mm² TFT channels + 1.59 mm² capacitors), no routing/pads, plus the host |
| Accuracy | any model (float linear 73.7 % CV, WS-01) | same | 68.9 % (FC-01) |

**Conclusion.** In this architecture Tortoise loses on energy, size, accuracy, interconnect count (10 driven lines +
5 outputs + supply vs 6 sensor lines) and complexity, because its host must digitise the inputs and stay awake for the
≈ 2.2 ms race anyway, which costs more than computing the classifier. A foil classifier could make sense only under
conditions argued (not shown) in PRIOR_ART.md §3: sensor-to-time conversion on the foil (no ADC, few lines),
a disposable dressing with a reusable rigid host outside it, nothing rigid on the wound side, printed unit cost.

### 4.3 What this does not show
Not a systematic review (about 40 queries); abstracts only; the MCU numbers are datasheet typicals with an assumed
cycle count, no MCU was programmed; sensor front-ends, radio and battery are counted on neither side; Tortoise's area
is a channel + capacitor lower bound, not a layout; its host floor is one MCU's LPM0 current, not a host design.

## 5. Deviations from the protocols (all dated in DECISIONS.md, each recorded before the runs it affects)
- **S2-D1:** the best Study 2 variant's 90-sample nominal run reuses its 20 nominal-check runs (same calibration and
  netlists).
- **Budget cuts after measuring ≈ 1 run/min** (and two machine restarts, progress log items 6 and 11): **S2-D2** (0.47 and
  0.45 V only for the better variant), **S3-D1** (20 instead of 40 held-out S samples per finalist), **S3-D2** (3 of the 5
  mismatch dies), and, in the protocols themselves, two Study 2 variants and two Study 3 finalists instead of three.
- **S1-D1:** no standby idles on the remaining mismatch dies (solver fallback took > 1 h per idle); no reported number
  depends on them.
- **Not run:** Study 1's secondary forced-mode-W cells (S1-F).
- **Post-hoc analyses (labelled, not protocol tests):** the Study 2 mechanism tables (stored waveforms), and the Study 3
  no-bias CV comparison (training data only).

## 6. What this report does not show (all studies)
- **Simulation only:** ngspice-42, a compact OTFT model at a reconstructed corner (`fitc10`, C10-DNTT on Si, read by
  eye), synthetic data. No device, circuit or sensor was measured.
- **Small N:** robustness and edge points use the 20-sample subset (one sample = 5 points); the test set has 90
  samples (Wilson half-width ≈ 9–10 points); the Study 3 selection used 20 held-out samples.
- **Assumed models:** size-scaled V_th mismatch (one anchor, 20 mV, 3–5 dies), global |V_th| and µ shifts as aging
  proxies, an ideal host.
- **Candidates are not qualified designs:** candidate-edgeA and candidate-bias were run only through the points listed in
  §2–§3; neither went through the full drift grid, mode-W chains, ramp-rate stress set or other mismatch models.
- **Study 4** is a targeted search with abstract-level claims and datasheet arithmetic, not a review or a measurement.

## 7. Reproduce
```
sh tools/setup_layout.sh                                   # /home/claude/w layout; ngspice-42; pip -r results/weights_schemeA/requirements.txt
cd results/wrapup/scripts
python3 s1_modew.py cal 4 && python3 s1_modew.py runs 4 && python3 s1_modew.py check && python3 s1_summary.py
python3 s2_mechanism.py                                    # needs the host_v21 E1 / host_v2 C3 waveforms (not included; regenerate them first)
python3 s2_runs.py edge R10.2-edgeA 4; python3 s2_runs.py edge R10.2-edgeB 4
python3 s2_runs.py edge2 x 4; python3 s2_runs.py nominal90 R10.2-edgeA 4; python3 s2_runs.py stress R10.2-edgeA; python3 s2_summary.py
python3 s3_train.py check; python3 s3_runs.py K 4; python3 s3_chain.py          # recal, CV, finalists, S runs, selection
python3 s3_runs.py test 4; python3 s3_runs.py stress; python3 s3_runs.py mm 4; python3 s3_summary.py eval; python3 s3_nobias_cv.py
python3 s4_mcu.py                                          # datasheet figures are in the script (sources: prior_art/)
cd ../../.. && python3 tools/check_results_index.py && python3 tools/check_concept.py
```
Runners are resumable (each skips finished per-run JSONs). Summaries are recomputed from the committed per-run JSONs
without SPICE (`s1_summary.py`, `s2_summary.py`, `s3_summary.py cv|select|eval`, `s4_mcu.py`). Per-run JSONs are included;
waveforms, netlists and draws are not included in this release (re-running the studies regenerates them).
