# Tortoise scheme A: retrained weights at the C10-DNTT corner (`fitc10`, Variant 3)

**Status: complete (2026-10-26).** Frozen circuit (campaign Variant 3 at `fitc10`); only the finger counts change. Protocol, amendments and their timing: [DECISIONS.md](DECISIONS.md) (W0–W15). Every table below is generated from `summary/*.json` by `scripts/report_tables.py` (this file is assembled from `scripts/REPORT_template.md`); every summary is recomputed from the per-run JSONs in `raw/` by the script named next to it.

## 1. Summary
- **Final weights** (`weights/FINAL_frozen.npy` = cand_a: margin-maximising, column sums 58/60/60/60/59, 21 non-empty banks, **134 TFTs**). Selected by the pre-registered rule; frozen and committed before any test run.
- **Test accuracy (A2, N = 90, run once):**
  - **62/90 = 68.9 %** (Wilson 95 % 58.7–77.5 %), the same as the old weights' 62/90 = 68.9 % (58.7–77.5 %).
  - Paired per sample: 6 gained, 6 lost, exact McNemar p = 1.0.
  - **Validity 82/90 = 91.1 %** (83.4–95.4 %) against 87/90 = 96.7 % (90.7–98.9 %), from 8 near-tie double latches against 3.
- **Why there was little to gain (A0, N = 210 training, nested group CV 10 × 5):**
  - float linear classifier 73.7 % (SD 1.4 over repeats);
  - the crossbar's form (no bias, equal column sums) 67.9 % (SD 1.0);
  - integer fingers with column sums 60: 68.1 % (SD 1.4);
  - old weights 70.0 % in-sample.
  - **The limit is the bias-free hardware form, not the particular weights.**
- **Surrogate** (calibrated on 40 training runs):
  - agrees with SPICE on 40/40 winners and 40/40 outcomes on held-out training samples;
  - 30/30 on mismatched dies;
  - 20/20 with unequal column sums;
  - 90/90 winners and 88/90 outcomes on the test set.
  - Resolve threshold G_res = 8.7 µs (bracket 6.9–10.5 µs); lock latency median 19.3 µs (N = 36).
- **Selection (A1, SPICE on 40 held-out training samples):** all three candidates 25/40 (47.0–75.8 %); old weights 26/40 (49.5–77.9 %). Co-optimised host timing (option d) found no better timing, so there is no second set.
- **Robustness (A3, 20-sample subset, N = 20 per point):**
  - Same working window as the old weights: with fixed levels, |V_th| 0.55–0.75 V and µ ×0.75–1.25. With re-trimmed levels: 65/65/60/50 % at 0.75/0.85/0.95/1.05 V, against 75/70/65/55 %.
  - 0–2 samples below the old weights at most corners.
  - Size-scaled V_th mismatch: **66/100** (56.3–74.5 %) and **61/100** (51.2–70.0 %) at anchors 20/35 mV, against 64/100 and 57/100 (paired p = 0.845 / 0.503).
- **Stress:** **0/134 TFTs above 3.5 V** in 5 extreme runs; worst X80 3.340 V; crossbar maximum 2.433 V.
- **Leakage audit (A4):** an independent audit (run separately, given only the repository and DECISIONS.md) found **no test-set leakage and no blocking issue**, and every recomputed number matched. One should-fix (the old weights were an undeclared optimiser start) and several minor rounding/wording items were fixed, and their deviations logged as W16 (§7).
- **Bottom line:** under scheme A at `fitc10`, retraining within the hardware constraints gives **the same test accuracy, a non-significant gain under mismatch, and lower nominal validity.** The weights weren't the limit; the missing per-class bias is (§2, §9).

## 2. Ceilings: how much there is to gain (A0, training data only)
Nested group cross-validation on the 210 training samples (21 acquisition groups; 5 folds × 10 repeats; regularisation chosen inside each training fold). Accuracy = argmax of the linear score, no circuit. Source: [A0_ceilings.json](summary/A0_ceilings.json), `scripts/ceilings.py`.

| Classifier | CV accuracy, mean of 10 repeats (SD over repeats) | Range over repeats | Training accuracy |
|---|---|---|---|
| Float linear, per-class bias, free weights (multinomial LR) | 73.7 % (1.4) | 71.4 %–75.7 % | 79.0 % |
| Float linear, bias (Crammer–Singer SVM) | 73.8 % (0.9) | 72.4 %–75.2 % | — |
| Float linear, bias (one-vs-rest SVM) | 72.7 % (1.1) | 71.0 %–74.3 % | — |
| Float linear, bias (shrinkage LDA) | 73.4 % (1.0) | 71.9 %–74.8 % | — |
| Float, no bias, free column sums | 73.9 % (1.3) | 71.4 %–75.2 % | 77.2 % |
| Float, bias, equal column sums | 73.0 % (1.4) | 70.5 %–74.8 % | 77.3 % |
| **Float, no bias, equal column sums = crossbar form** (non-negativity is free) | 67.9 % (1.0) | 66.2 %–69.5 % | 71.6 % |
| Integer fingers (Σ = 60, 15–21 banks): rounded crossbar-form LR | 67.4 % (1.8) | 64.8 %–69.5 % | 70.9 % |
| Integer fingers: + local search on the training count | 68.1 % (1.4) | 65.7 %–69.5 % | 72.6 % |
| Integer fingers: + MILP polish | 68.0 % (1.3) | 65.7 %–69.5 % | 72.8 % |
| Old weights (trained on all 210: **in-sample**) | 70.0 % (0.0) | 70.0 %–70.0 % | — |

**How the crossbar handles sign and offset.** Adding the same amount to one row of every class (the same extra current into every rail) doesn't change which rail wins, so any float weight matrix can be shifted row by row until it is non-negative: **non-negativity costs nothing**. What the crossbar can't do with equal column sums is a per-class bias: the WMIN pedestal puts the same 60·WMIN finger·µs on every rail. "No bias + equal column sums" is the binding pair (67.9 % against ≈ 73–74 % for a general linear classifier).

**Reading.**
- **The missing bias costs ≈ 6 points.** Either a bias or free column sums brings the float classifier back to 73–74 %.
- **With column sums fixed at 60 there is nothing to gain in nominal accuracy:** integer fingers reach 67.4–68.1 % in CV, and the old weights already score 70.0 % on the training data (in-sample, so optimistic).
- **Unequal column sums give the race a bias** (amendment W13). With nₖ = Σᵢ F[i,k], the calibrated race model gives tₖ = (Θ − R − c₀)/(γ nₖ) − α·WMIN/γ − (α T₁/γ)(sₖ/nₖ). The pedestal term is common, but a class with fewer fingers starts further behind. Column sums of 50–60 were therefore admitted as a CV-selected option, inside the 60-finger budget.

## 3. Surrogate calibration (A0)
The surrogate (`scripts/surrogate.py`) is a physical race model. Rail k reaches Vₖ = Rₖ + α Σᵢ F[i,k] g1[i,k] (WMIN + xᵢT₁) + c₀ at the start of C2, then rises at γ Σᵢ F[i,k] g2[i,k]. Its trip time is tₖ = (Θₖ − Vₖ)/slope. A sample is correct if its class trips first, the runner-up trails by ≥ G_res, and nothing trips during C1. g1/g2 are the bank-current factors for a V_th offset, taken from the device model itself (`scripts/bank_dc.py`: dg/dV = −2.26 /V at V₁ and −7.04 /V at V₂; the same at every re-trimmed |V_th| because the overdrive is constant).

All calibration runs use **training samples only**; all but the unequal-sum check use the old weights:
- K: 40 runs, 8 per class, chosen by the old weights' software margin, including 3 near ties per class;
- held-out S: 40 runs, 4 whole acquisition groups, never used for fitting;
- 11 one-device sensitivity runs;
- 30 mismatched-die runs;
- 32 re-trimmed-corner runs;
- 20 runs with unequal column sums.

Each weight set gets its own warm start, built by the campaign's D7 procedure on training sample #123 (class 5) from the lab prior. The campaign's #81-derived warm start isn't used. Sources: [A0_calibration.json](summary/A0_calibration.json), [A0_mismatch.json](summary/A0_mismatch.json), [A0_retrim.json](summary/A0_retrim.json), [A0_colsum_check.json](summary/A0_colsum_check.json), [surrogate_params.json](summary/surrogate_params.json).

| Quantity (K, 40 runs, old weights) | Value |
|---|---|
| C1 transfer α (V per finger·µs), c₀ | 9.9968e-05, 23.0 mV; rms residual 0.13 mV over 200 rails |
| Gap slope s_g (losers' gap vs rail deficit) | 0.642 mV/µs (160 points, median relative residual 0.9 %) |
| Average C2 slope s̄, gap factor s̄/s_g | 0.6248 mV/µs, 0.9735 |
| Effective trip level Θ_k (V) | 2.2082, 2.2094, 2.2089, 2.2106, 2.2102; trip-time residual 2.06 µs rms |
| Rail reset level R_k (V) | 0.8946, 0.8977, 0.8973, 0.8969, 0.8994 |
| Resolve threshold G_res | 8.70 µs (largest failed gap 6.88 µs, smallest valid 10.513 µs; 4/40 invalid) |
| Lock latency (valid runs) | median 19.26 µs, range 19.07–20.28 µs (N = 36) |
| Gap scale vs lab rev10 schemeA.py model | SPICE/model median 0.839 (r = 0.9989, N = 36) |

| Agreement with SPICE | N | Winner | Validity | Correct/incorrect | Gap r | Gap SPICE/surrogate (median) | Gap error median / max |
|---|---|---|---|---|---|---|---|
| K, in-sample | 40 | 40/40 | 39/40 | 40/40 | 0.9998 | 0.967 | 2.3 / 5.1 µs |
| K, 5-fold CV inside K | 40 | 40/40 | 38/40 | 40/40 | — | — | — |
| **S, held out (40)** | 40 | 40/40 | 40/40 | 40/40 | 0.9998 | 0.979 | 2.5 / 6.1 µs |

| Device (class chain) | W·L (µm²) | Effect per volt of ΔV_th |
|---|---|---|
| Reset switch X75 (rail start level) | 8000 | +0.999 (reset level +0.984) |
| sense X81 (trip level) | 7020 | -1.0143 |
| detect_load X82 (trip level) | 2400 | +0.1087 |
| trip_driver X83 (trip level) | 2000 | +0.1590 |
| latch_load_A X84 (trip level) | 1200 | -0.0188 |
| cross_X X85 (trip level) | 300 | +0.0050 |
| cross_Y X86 (trip level) | 300 | +0.0000 |
| latch_load_B X87 (trip level) | 600 | +0.0013 |
| Crossbar bank X6 (38 fingers), +30 mV | — | trip shift SPICE 206.2 µs vs surrogate 208.0 µs |

Mismatch check (3 dies × 10 K samples, anchor 35 mV, surrogate fed the same draws): winner 30/30, validity 30/30, correct/incorrect 30/30; the die changed the SPICE winner in 11 runs and the surrogate predicted all 11.

| Re-trimmed \|V_th\| | Runs | ref − reset (V) | Θ shift (mV) | Trips in C1 (SPICE / surrogate) | Winner / validity / outcome agreement |
|---|---|---|---|---|---|
| 0.55 V | 8 | 0.515 | +16.0 | 0 / 0 | 8/8, 8/8, 8/8 |
| 0.75 V | 8 | 0.443 | -14.5 | 0 / 0 | 8/8, 8/8, 8/8 |
| 0.85 V | 8 | 0.405 | -47.3 | 0 / 0 | 8/8, 8/8, 8/8 |
| 0.95 V | 8 | 0.366 | -77.5 | 1 / 2 | 8/8, 6/8, 6/8 |

Unequal column sums (W13 check, `probe_le60`, sums [58, 60, 60, 60, 58], 20 K runs): winner 20/20, validity 20/20, correct/incorrect 20/20; C2 slope ratio of the 58-finger columns 0.969 (expected 58/60 = 0.967).

**Reading.**
- **The circuit is very linear in scheme A.** The C1 charge follows the finger-weighted pulse time to 0.13 mV rms. The gap between two rails is their C1 voltage difference divided by the C2 slope.
- **What the old campaign called the "gap scale (≈ 0.84×)"** is re-derived here on training data (0.839). It's the ratio of SPICE to the lab-calibrated `rev10/eval/schemeA.py` model, which this surrogate replaces.
- **Per-class trip levels** differ by ≤ 2.4 mV once fitted with a common slope. A first fit with per-class medians was confounded with race length; the change is logged in the campaign's progress log (item 6; not included in this release).
- **Resolve threshold G_res = 8.7 µs.** Near-tie failures are double latches. In K the boundary lies between 6.9 µs (failed) and 10.5 µs (valid); on the test set (§5) a run with an 8.8 µs gap failed and one with 9.8 µs was valid. The boundary is soft at the ±2–4 µs level, which is the surrogate's gap error there (2–3 µs in K, 3.5 and 4.1 µs for the two test-set misses).
- **Lock latency** is 19.3 µs (median). It's reported but doesn't decide validity: valid runs exist with gaps below it, as in the campaign.
- **Mismatch enters through three paths:**
  - the reset switch shifts the rail start level one-for-one (+1.00 per V);
  - the comparator sense device shifts the trip level one-for-one (−1.01 per V); the trip driver and detect load add +0.16 and +0.11 per V, the latch devices < 0.02 per V;
  - each crossbar bank scales its current; in C2 this dominates, since +30 mV on one 38-finger bank moved the trip by 206 µs.
- **With size-scaled σ,** a column's C2-slope spread doesn't depend on how its fingers are split between banks; only the column total matters.

## 4. Candidates and how they were selected (A1)
**Pool and splits.**
- **Selection set S** (4 whole groups, 40 samples): never used to fit, calibrate or select anything before W9. One caveat, found by the audit (W16.1): one of the optimiser starts, the old weights, had been fitted on all 210 training samples, S included (see the end of this section).
- **Training pool T** (17 groups, 170 samples): candidates were trained on it, with hyperparameters chosen by group CV (5 folds × 4 repeats = 20 splits).
- **Selection score** (W8): S = 0.5·A_nom + 0.25·A_mm + 0.25·A_rt, all surrogate accuracies on the validation folds:
  - A_nom: nominal die;
  - A_mm: 500 analytic dies, size-scaled V_th, anchors 20 and 35 mV;
  - A_rt: re-trimmed |V_th| 0.55–0.95 V, where a trip during C1 counts as a failure.

**Families and optimisers** (all integer, 15–21 non-empty banks, column sums = 60 or 50–60):
- **(a) Margin-maximising:** maximise the number of training samples whose class wins by ≥ G_res + m on the nominal surrogate.
  - Starts: rounded constrained logistic regression (3 regularisations) and the old weights.
  - Greedy integer descent on the exact count, then (for sums = 60) an exact MILP polish in HiGHS, warm-started, with a 3000-node budget. All 140 MILP solves hit the node budget (median gap 25 %), so none is proven optimal.
  - m ∈ {0, 5, 10, 20, 30, 45, 60} µs.
- **(b) Mismatch-aware:** expected accuracy over 128 training dies (separate from the evaluation dies), with the mismatch injected as in §3.
  - Simulated annealing (20 000 moves, 3 starts), then greedy descent.
  - Smoothing τ ∈ {0, 2, 5} µs, plus (10, 0), (20, 0), (5, 15), (5, 30) µs added by amendment W14 after (b) was seen to overfit its training dies (≈ 72 % own-sample expected accuracy against ≈ 64 % in CV).
- **(c) Re-trim-aware:** (b) averaged over re-trimmed |V_th| 0.55–0.95 V (same grid).
- **(d) Co-optimised timing (W15):** screened T₁ ∈ {170…260} µs × WMIN ∈ {20, 40} µs with the (c)-best configuration. **The frozen timing scored best** (S = 0.678 on the 5 screening splits). Longer T₁ helps the mismatch term slightly, but trips during C1 collapse the re-trimmed 0.95 V corner (49–55 % at T₁ 230 µs, 46–50 % at 260 µs). **So there is no co-optimised-timing set.** Source: [A1_d_screen.json](summary/A1_d_screen.json).

| Family | Column sums | Config | **S ×100** (SD over 4 repeats) | A_nom | A_mm (20 / 35 mV) | A_rt | A_rt at 0.95 V | Banks (median) | Smallest column sum (median) |
|---|---|---|---|---|---|---|---|---|---|
| (a) margin | = 60 | m = 0 µs | **64.7** (2.4) | 66.3 % | 60.9 % (63.3 % / 58.5 %) | 65.3 % | 61.2 % | 21.0 | 60.0 |
| (a) margin | = 60 | m = 5 µs | **65.1** (2.7) | 66.8 % | 61.0 % (63.7 % / 58.3 %) | 65.7 % | 61.3 % | 21.0 | 60.0 |
| (a) margin | = 60 | m = 10 µs | **66.2** (1.0) | 67.7 % | 62.9 % (65.3 % / 60.6 %) | 66.5 % | 61.9 % | 21.0 | 60.0 |
| (a) margin | = 60 | m = 20 µs | **66.7** (1.7) | 68.2 % | 63.1 % (65.5 % / 60.6 %) | 67.4 % | 64.0 % | 21.0 | 60.0 |
| (a) margin | = 60 | m = 30 µs | **67.6** (2.4) | 69.0 % | 64.4 % (66.5 % / 62.2 %) | 67.9 % | 64.4 % | 21.0 | 60.0 |
| (a) margin | = 60 | m = 45 µs | **66.8** (0.8) | 67.8 % | 64.8 % (66.5 % / 63.2 %) | 66.6 % | 61.9 % | 21.0 | 60.0 |
| (a) margin | = 60 | m = 60 µs | **66.5** (1.2) | 67.2 % | 65.4 % (66.6 % / 64.2 %) | 66.1 % | 61.6 % | 21.0 | 60.0 |
| (a) margin | 50–60 | m = 0 µs | **66.1** (5.0) | 67.4 % | 63.0 % (65.2 % / 60.8 %) | 66.8 % | 64.4 % | 21.0 | 58.0 |
| (a) margin | 50–60 | m = 5 µs | **66.4** (1.4) | 67.7 % | 63.2 % (65.0 % / 61.3 %) | 67.2 % | 65.6 % | 21.0 | 57.5 |
| (a) margin | 50–60 | m = 10 µs | **67.9** (1.5) | 69.4 % | 64.2 % (66.3 % / 62.1 %) | 68.5 % | 65.0 % | 21.0 | 58.0 |
| (a) margin | 50–60 | m = 20 µs | **68.4** (1.9) | 69.9 % | 65.1 % (67.3 % / 62.9 %) | 68.7 % | 65.0 % | 21.0 | 58.0 |
| (a) margin | 50–60 | m = 30 µs ◀ best | **69.1** (1.4) | 70.4 % | 66.1 % (68.4 % / 63.8 %) | 69.6 % | 66.3 % | 21.0 | 58.0 |
| (a) margin | 50–60 | m = 45 µs | **67.7** (1.3) | 68.8 % | 65.4 % (67.0 % / 63.7 %) | 67.6 % | 62.7 % | 21.0 | 58.0 |
| (a) margin | 50–60 | m = 60 µs | **65.8** (0.7) | 66.5 % | 64.5 % (65.7 % / 63.3 %) | 65.7 % | 61.8 % | 20.0 | 58.5 |
| (b) mismatch | = 60 | τ = 0 µs | **63.3** (2.4) | 63.8 % | 62.7 % (63.8 % / 61.6 %) | 62.9 % | 58.5 % | 19.0 | 60.0 |
| (b) mismatch | = 60 | τ = 2 µs | **63.9** (1.6) | 64.6 % | 63.1 % (64.2 % / 62.0 %) | 63.5 % | 59.3 % | 18.5 | 60.0 |
| (b) mismatch | = 60 | τ = 5 µs | **64.1** (2.3) | 64.9 % | 62.9 % (64.0 % / 61.8 %) | 63.7 % | 59.1 % | 18.0 | 60.0 |
| (b) mismatch | = 60 | τ = 10 µs | **64.4** (2.2) | 65.3 % | 63.0 % (64.0 % / 61.9 %) | 64.0 % | 59.3 % | 19.0 | 60.0 |
| (b) mismatch | = 60 | τ = 20 µs | **64.4** (1.6) | 65.2 % | 63.4 % (64.4 % / 62.4 %) | 64.0 % | 59.1 % | 18.0 | 60.0 |
| (b) mismatch | = 60 | τ = 5, m = 15 µs | **64.2** (1.4) | 64.9 % | 63.6 % (64.4 % / 62.7 %) | 63.7 % | 59.0 % | 18.0 | 60.0 |
| (b) mismatch | = 60 | τ = 5, m = 30 µs | **63.9** (2.0) | 64.6 % | 63.6 % (64.2 % / 62.9 %) | 63.1 % | 57.2 % | 16.0 | 60.0 |
| (b) mismatch | 50–60 | τ = 0 µs | **66.0** (2.0) | 66.6 % | 63.9 % (65.4 % / 62.5 %) | 66.9 % | 66.6 % | 18.0 | 53.0 |
| (b) mismatch | 50–60 | τ = 2 µs | **67.0** (2.0) | 68.1 % | 64.4 % (65.9 % / 62.9 %) | 67.4 % | 66.2 % | 17.0 | 53.0 |
| (b) mismatch | 50–60 | τ = 5 µs | **66.6** (1.4) | 67.5 % | 64.3 % (65.8 % / 62.7 %) | 67.0 % | 65.7 % | 18.0 | 53.0 |
| (b) mismatch | 50–60 | τ = 10 µs | **66.8** (1.2) | 67.8 % | 64.2 % (65.7 % / 62.8 %) | 67.2 % | 65.4 % | 17.0 | 52.0 |
| (b) mismatch | 50–60 | τ = 20 µs ◀ best | **67.4** (2.4) | 68.5 % | 65.0 % (66.4 % / 63.6 %) | 67.7 % | 65.6 % | 17.0 | 53.0 |
| (b) mismatch | 50–60 | τ = 5, m = 15 µs | **66.1** (1.8) | 66.8 % | 64.3 % (65.5 % / 63.1 %) | 66.6 % | 65.7 % | 16.0 | 52.5 |
| (b) mismatch | 50–60 | τ = 5, m = 30 µs | **66.9** (1.9) | 67.5 % | 65.4 % (66.5 % / 64.2 %) | 67.3 % | 66.2 % | 15.0 | 51.5 |
| (c) re-trim | = 60 | τ = 0 µs | **65.4** (2.3) | 66.5 % | 63.1 % (64.5 % / 61.6 %) | 65.8 % | 62.9 % | 20.0 | 60.0 |
| (c) re-trim | = 60 | τ = 2 µs | **65.0** (2.0) | 65.9 % | 63.1 % (64.5 % / 61.6 %) | 65.2 % | 62.7 % | 20.0 | 60.0 |
| (c) re-trim | = 60 | τ = 5 µs | **65.1** (1.8) | 66.0 % | 63.1 % (64.5 % / 61.7 %) | 65.4 % | 62.8 % | 20.0 | 60.0 |
| (c) re-trim | = 60 | τ = 10 µs | **65.2** (1.7) | 66.0 % | 63.3 % (64.6 % / 61.9 %) | 65.3 % | 62.5 % | 20.0 | 60.0 |
| (c) re-trim | = 60 | τ = 20 µs | **65.1** (1.9) | 65.9 % | 63.5 % (64.8 % / 62.3 %) | 65.1 % | 61.9 % | 20.0 | 60.0 |
| (c) re-trim | = 60 | τ = 5, m = 15 µs | **64.4** (1.7) | 65.0 % | 63.5 % (64.6 % / 62.5 %) | 64.2 % | 61.3 % | 18.0 | 60.0 |
| (c) re-trim | = 60 | τ = 5, m = 30 µs | **66.0** (2.2) | 66.6 % | 64.7 % (65.8 % / 63.7 %) | 65.9 % | 62.5 % | 17.0 | 60.0 |
| (c) re-trim | 50–60 | τ = 0 µs | **66.9** (2.0) | 67.8 % | 63.8 % (65.6 % / 62.1 %) | 68.0 % | 67.8 % | 18.0 | 52.0 |
| (c) re-trim | 50–60 | τ = 2 µs | **67.2** (1.7) | 68.4 % | 63.8 % (65.6 % / 62.1 %) | 68.0 % | 67.1 % | 18.0 | 53.0 |
| (c) re-trim | 50–60 | τ = 5 µs | **66.9** (2.1) | 67.8 % | 64.1 % (65.8 % / 62.3 %) | 67.9 % | 67.5 % | 17.5 | 52.0 |
| (c) re-trim | 50–60 | τ = 10 µs ◀ best | **67.3** (2.8) | 68.2 % | 64.5 % (66.2 % / 62.8 %) | 68.1 % | 67.9 % | 17.0 | 52.0 |
| (c) re-trim | 50–60 | τ = 20 µs | **66.5** (1.7) | 67.2 % | 64.0 % (65.6 % / 62.4 %) | 67.7 % | 67.8 % | 17.0 | 52.5 |
| (c) re-trim | 50–60 | τ = 5, m = 15 µs | **66.0** (1.5) | 66.6 % | 64.2 % (65.4 % / 63.0 %) | 66.5 % | 66.6 % | 17.0 | 52.0 |
| (c) re-trim | 50–60 | τ = 5, m = 30 µs | **66.3** (2.5) | 66.3 % | 65.1 % (66.3 % / 63.9 %) | 67.4 % | 68.1 % | 15.0 | 51.0 |
| reference: old weights in sample | — | — | 69.1 | 70.0 % | 67.3 % (68.8 % / 65.7 %) | 69.1 % | 65.3 % | — | — |

**Reading of the CV.**
- **Margin maximisation (a) beats the mismatch-aware objectives (b, c) even on their own mismatch and re-trim components.** The annealer fits individual training samples and dies; a plain margin regularises better with 130–140 training samples per split.
- **Unequal column sums help every family by 1–3 points of S.**
- **The best candidate's CV score equals the old weights' training-set score** (0.691 both). The old weights' figure is in-sample and therefore optimistic, so a small CV gain over them is plausible, but it isn't resolvable.

**SPICE decision on S (W9).** The best configuration of each family was retrained on all of T, given its own warm start, and run in SPICE on the 40 held-out S samples. The rule: highest SPICE accuracy wins, ties go to the higher CV score. The old weights are run as a reference only. Source: [A1_select.json](summary/A1_select.json).

| Weights | Banks / TFTs | Column sums | CV score S | **SPICE on S: correct** (Wilson 95 %) | Valid | Surrogate agreement (winner / outcome) | vs old on S (both / old only / new only / neither) |
|---|---|---|---|---|---|---|---|
| old (reference) | 21 / 134 | [60, 60, 60, 60, 60] | — | **26/40** (49.5–77.9 %) | 40/40 | 40/40 / 40/40 | — |
| cand_a ◀ winner | 21 / 134 | [58, 60, 60, 60, 59] | 69.1 | **25/40** (47.0–75.8 %) | 39/40 | 40/40 / 40/40 | 24 / 2 / 1 / 13 |
| cand_b | 17 / 130 | [52, 58, 59, 60, 55] | 67.4 | **25/40** (47.0–75.8 %) | 39/40 | 40/40 / 40/40 | 24 / 2 / 1 / 13 |
| cand_c | 17 / 130 | [50, 54, 56, 57, 52] | 67.3 | **25/40** (47.0–75.8 %) | 37/40 | 40/40 / 39/40 | 23 / 3 / 2 / 12 |

- **The three candidates tie at 25/40,** so the CV score picks **cand_a** (family a, column sums 50–60, m = 30 µs). It was frozen with its SHA-256 and committed (`705d260`) before any test-set run. Its column sums are 58/60/60/60/59, with 21 non-empty banks (134 TFTs, the same as now).
- **On S the old weights score 26/40,** one more than every candidate; with N = 40 that difference is noise. **The selection step found no evidence that any candidate beats the old weights.**
- **The surrogate called every winner in all 160 S runs.**
- **Order of S runs:** cand_a's S runs ran before (b)/(c) finished, and by my log their results were not opened until all three candidates were frozen. Four lines of cand_b's log were seen while checking CPU load (progress log items 13 and 16; not included in this release).
  - The audit notes that the first claim can't be verified from the record (the run log was committed).
  - There was also no channel through which the S results could have mattered: W14 was committed before those S runs, and (b)/(c) ran unattended from fixed grids.

**Sensitivity to the undeclared old-weights start (audit finding 1, W16.1).**
- The old weights were one of the optimiser starts in every family, and they had been fitted on all 210 training samples.
- The CV of the three chosen configurations was re-run without that start; everything else (splits, seeds, dies) is unchanged. Source: [A4_no_old_start.json](summary/A4_no_old_start.json), `scripts/no_old_start.py`.

| Configuration | CV score S ×100, as run (with the old-weights start) | S ×100 without it | A_nom / A_mm / A_rt without it | Splits whose weights changed |
|---|---|---|---|---|
| a le60 30 | 69.1 (1.4) | **69.4** (1.4) | 70.7 % / 66.0 % / 69.9 % | 3/20 |
| b le60 20 | 67.4 (2.4) | **68.1** (1.0) | 69.4 % / 65.3 % / 68.4 % | 3/20 |
| c le60 10 | 67.3 (2.8) | **66.8** (2.0) | 67.7 % / 64.3 % / 67.6 % | 7/20 |

- **Result:** without the old-weights start the three chosen configurations score S = 0.694 (a), 0.681 (b) and 0.668 (c), against 0.691, 0.674 and 0.673 as run. The weights changed in 3, 3 and 7 of the 20 splits.
- **The order a > b > c is unchanged,** and with it the W9 tie-break that picked cand_a.
- **Not re-run:** whether some other configuration would have overtaken the chosen one within a family; that would repeat all of A1.
- **No final candidate descends from the old weights:** cand_a's run and the a_m20 start used by cand_b/cand_c all won from the `lr0.001` start.

## 5. Test-set results compared with the old weights (A2, run once)
The frozen weights were run once on all 90 test samples, nominal `fitc10`, own warm start, plus the campaign's 10-sample chain. The old weights' per-sample results are the campaign's Variant 3 Phase 1 runs, which used the #81-derived warm start; the different warm starts are a confound of a few µs of gap (chain below). Sources: [A2_FINAL_frozen.json](summary/A2_FINAL_frozen.json), [A2_FINAL_frozen_runs.csv](summary/A2_FINAL_frozen_runs.csv), `scripts/eval_test.py`.

| Measure | New weights (FINAL_frozen = cand_a) | Old weights (campaign Phase 1, Variant 3) |
|---|---|---|
| SPICE accuracy (invalid = wrong) | **62/90 = 68.9 %** (58.7–77.5 %) | 62/90 = 68.9 % (58.7–77.5 %) |
| Validity | 82/90 = 91.1 % (83.4–95.4 %) | 87/90 = 96.7 % (90.7–98.9 %) |
| Failures | multi_latched ×8 | multi_latched ×3 |
| Software argmax accuracy (same weights) | 71.1 % | 70.0 % |
| Surrogate: accuracy / winner agreement / outcome agreement | 71.1 % / 90/90 / 88/90 | — |
| Surrogate vs SPICE gap (same winner and runner-up) | r = 0.9989, SPICE/surrogate median 0.972 (N = 81) | — |
| Runner-up gap, valid runs: median / 5th pct / min | 85.3 / 17.8 / 9.8 µs | 102.1 / 27.4 / 10.7 µs |
| Valid runs with gap < 20 µs | 9 | 4 |
| Lock latency, valid runs: median (range) | 19.4 µs (19.1–20.4) | 19.2 µs (19.1–20.0) |
| Race from C2: median (range) | 918 µs (487–1225) | 870 µs (493–1148) |
| Trips during C1 | 0 | 0 |
| TFTs / non-empty banks | 134 / 21 | 134 / 21 |

**Paired with the old weights (same 90 samples):** both correct 56, old only 6, new only 6, both wrong 22; difference +0.0 points; exact two-sided McNemar p = 1.000.

Confusion matrix, new weights:

| label \ SPICE | 1 | 2 | 3 | 4 | 5 | invalid |
|---|---|---|---|---|---|---|
| 1 | 14 | 3 | 0 | 0 | 0 | 1 |
| 2 | 2 | 15 | 1 | 0 | 0 | 0 |
| 3 | 2 | 2 | 6 | 3 | 0 | 5 |
| 4 | 0 | 2 | 2 | 11 | 2 | 1 |
| 5 | 0 | 0 | 1 | 0 | 16 | 1 |

Confusion matrix, old weights (campaign):

| label \ SPICE | 1 | 2 | 3 | 4 | 5 | invalid |
|---|---|---|---|---|---|---|
| 1 | 16 | 1 | 0 | 0 | 0 | 1 |
| 2 | 3 | 15 | 0 | 0 | 0 | 0 |
| 3 | 6 | 2 | 5 | 2 | 1 | 2 |
| 4 | 1 | 2 | 1 | 8 | 6 | 0 |
| 5 | 0 | 0 | 0 | 0 | 18 | 0 |

**Chain (test 30–39 in sequence, from this weight set's warm start):** same outcome as the independent runs 10/10; correct 8/10; largest first-trip shift 4.44 µs; largest gap shift 6.58 µs; largest rail reset-level change 5.61 mV.

**Reading.**
- **The retrained weights don't improve test accuracy:** 62/90 for both, 6 samples gained and 6 lost (McNemar p = 1.0). This matches A0 (the hardware form is at its ceiling) and A1 (no candidate beat the old weights on S).
- **Validity fell from 87/90 to 82/90.** The new weights have more near ties on the test set: runner-up gap median 85 against 102 µs, 9 against 4 valid runs below 20 µs, and 8 double latches against 3.
  - Six of the eight double-latched samples were misclassified by the old weights too; the two that cost a sample are #47 and #73.
  - In three of the eight the first tripper wasn't the label anyway.
  - The margin objective rewards the count of training samples above G_res + 30 µs, not the overall gap distribution. On the test groups that trade didn't pay.
- **The surrogate predicted the winner of all 90 test runs and the outcome of 88.** The two misses are near ties (SPICE gaps 7.3 and 8.3 µs, predicted 11.4 and 11.8 µs). So the surrogate's 71.1 % was ≈ 2 points optimistic, which is small: the surrogate isn't what limited the result. The new weights simply generalise no better than the old ones.
- **Lock latency (19.4 µs) and race times (median 918 µs, max 1225 µs)** are as before. The class 1 and 5 columns have 58 and 59 fingers, so they ramp 3.3 % and 1.7 % slower in C2. No trip happened during C1.
- **History:** the chain reproduces all 10 independent outcomes; the largest history-induced gap shift is 6.6 µs.

## 6. Robustness and stress compared with the old weights (A3)
Same 20-sample test subset as the campaign (`summary/phase3_subset.json` of the campaign, 4 per class), same corners, 2500 µs window and seeds. The nominal warm start of each weight set is used for every point. The old weights' numbers are the campaign's Variant 3 runs, read from its per-run JSONs; failure labels use the campaign's `summarize.failure`. Sources: [A3_FINAL_frozen.json](summary/A3_FINAL_frozen.json), [A3_stress_FINAL_frozen.json](summary/A3_stress_FINAL_frozen.json), [A3_pairing_check.json](summary/A3_pairing_check.json), `scripts/robustness.py`, `scripts/stress.py`.

Fixed host levels (drift budget):

| Point | New: correct (Wilson 95 %) | New: valid | New: failures | Old: correct | Old: valid | Old: failures | Paired: new only / old only (exact McNemar p) | Race median new / old |
|---|---|---|---|---|---|---|---|---|
| nominal (0.65 V, µ ×1; A2 / campaign Phase 1 runs) | **13/20** (43.3–81.9 %) | 18/20 | multi_latched ×2 | 15/20 | 20/20 | — | 1 / 3 (p = 0.625) | 905 / 879 µs |
| \|V_th\| 0.45 V | **0/20** (0.0–16.1 %) | 0/20 | stuck_latched ×20 | 0/20 | 0/20 | stuck_latched ×20 | 0 / 0 (p = 1.000) | — / — µs |
| \|V_th\| 0.55 V | **13/20** (43.3–81.9 %) | 17/20 | multi_latched ×3 | 14/20 | 19/20 | multi_latched ×1 | 2 / 3 (p = 1.000) | 442 / 424 µs |
| \|V_th\| 0.75 V | **13/20** (43.3–81.9 %) | 17/20 | timeout ×3 | 13/20 | 18/20 | timeout ×2 | 3 / 3 (p = 1.000) | 2034 / 1984 µs |
| \|V_th\| 0.85 V | **0/20** (0.0–16.1 %) | 0/20 | timeout ×20 | 0/20 | 0/20 | timeout ×20 | 0 / 0 (p = 1.000) | — / — µs |
| \|V_th\| 0.95 V | **0/20** (0.0–16.1 %) | 0/20 | timeout ×20 | 0/20 | 0/20 | timeout ×20 | 0 / 0 (p = 1.000) | — / — µs |
| \|V_th\| 1.05 V | **0/20** (0.0–16.1 %) | 0/20 | timeout ×20 | 0/20 | 0/20 | timeout ×20 | 0 / 0 (p = 1.000) | — / — µs |
| µ ×0.5 | **9/20** (25.8–65.8 %) | 10/20 | timeout ×9, multi_latched ×1 | 8/20 | 10/20 | none_latched ×2, timeout ×6, multi_latched ×2 | 3 / 2 (p = 1.000) | 2300 / 2301 µs |
| µ ×0.75 | **14/20** (48.1–85.5 %) | 18/20 | multi_latched ×2 | 14/20 | 19/20 | multi_latched ×1 | 4 / 4 (p = 1.000) | 1455 / 1427 µs |
| µ ×1.25 | **13/20** (43.3–81.9 %) | 18/20 | multi_latched ×2 | 15/20 | 20/20 | — | 1 / 3 (p = 0.625) | 559 / 534 µs |

Re-trimmed host levels (process window):

| Point | New: correct (Wilson 95 %) | New: valid | New: failures | Old: correct | Old: valid | Old: failures | Paired: new only / old only (exact McNemar p) | Race median new / old | Strict (no trip in C1) new / old | Trips in C1 new / old |
|---|---|---|---|---|---|---|---|---|---|---|
| \|V_th\| 0.75 V (V₁ 1.72 / V₂ 2.3 V) | **13/20** (43.3–81.9 %) | 17/20 | multi_latched ×3 | 15/20 | 20/20 | — | 1 / 3 (p = 0.625) | 707 / 681 µs | 13/20 / 15/20 | 0 / 0 |
| \|V_th\| 0.85 V (V₁ 1.62 / V₂ 2.2 V) | **13/20** (43.3–81.9 %) | 17/20 | multi_latched ×3 | 14/20 | 19/20 | multi_latched ×1 | 2 / 3 (p = 1.000) | 504 / 477 µs | 13/20 / 14/20 | 0 / 0 |
| \|V_th\| 0.95 V (V₁ 1.52 / V₂ 2.1 V) | **12/20** (38.7–78.1 %) | 16/20 | multi_latched ×4 | 13/20 | 18/20 | multi_latched ×2 | 2 / 3 (p = 1.000) | 298 / 271 µs | 11/20 / 12/20 | 2 / 2 |
| \|V_th\| 1.05 V (V₁ 1.42 / V₂ 2.0 V) | **10/20** (29.9–70.1 %) | 14/20 | multi_latched ×6 | 11/20 | 15/20 | multi_latched ×5 | 1 / 2 (p = 1.000) | 86 / 60 µs | 8/20 / 7/20 | 7 / 9 |

Size-scaled V_th mismatch (3B-V), 5 dies × 20 samples per anchor, same seeds as the campaign:

| Point | New: correct (Wilson 95 %) | New: valid | New: failures | Old: correct | Old: valid | Old: failures | Paired: new only / old only (exact McNemar p) | Race median new / old | Median die new / old |
|---|---|---|---|---|---|---|---|---|---|
| anchor 20 mV | **66/100** (56.3–74.5 %) | 92/100 | multi_latched ×8 | 64/100 | 95/100 | multi_latched ×5 | 14 / 12 (p = 0.845) | 904 / 849 µs | 65 % / 65 % |
| anchor 35 mV | **61/100** (51.2–70.0 %) | 90/100 | multi_latched ×10 | 57/100 | 94/100 | multi_latched ×6 | 12 / 8 (p = 0.503) | 923 / 895 µs | 60 % / 60 % |

**Reading.**
- **The working window is unchanged.**
  - With fixed host levels the new weights work at |V_th| 0.55–0.75 V and µ ×0.75–1.25, fail at 0.45 V (latches stuck high, as before), and time out at ≥ 0.85 V (the C2 overdrive collapses, as before).
  - With re-trimmed levels they degrade from 0.85 to 1.05 V, like the old weights.
- **The new weights are 0–2 samples below the old weights at most corners,** mostly through more near-tie double latches (at every corner except µ ×0.5 and fixed 0.75 V). At µ ×0.5 they are one above. None of these differences is resolvable with N = 20.
- **At fixed |V_th| 0.75 V the new weights time out 3 times (old: 2).** The 58-finger class-1 column ramps 3 % slower in C2, so the slowest races (≈ 2.0–2.4 ms) get closer to the 2.5 ms window. W13 anticipated this.
- **At re-trimmed 1.05 V the new weights trip during C1 in 7 runs (old: 9)** and score 8/20 on the strict count (old: 7/20).
- **Size-scaled V_th mismatch (3B-V; the same dies as the campaign, paired per instance, see `A3_pairing_check.json`):**
  - **This is the only place the new weights come out ahead:** 66/100 vs 64/100 at the 20 mV anchor (paired McNemar p = 0.845), and 61/100 vs 57/100 at 35 mV (p = 0.503). The pairs share dies, so these p-values are only indicative.
  - That direction is what the margin objective aims for, but it isn't resolvable.
  - Validity is again lower: 92 vs 95 and 90 vs 94 of 100. All failures are near-tie double latches, with no lockout failure, stuck latch or timeout.
  - The median die is the same for both weight sets (65 % at 20 mV, 60 % at 35 mV). The new weights' dies send at most 30–41 % of their valid predictions to one class, so there's no per-class bias.

**Stress audit (5 extreme runs, crossbar included).** The runs were chosen by the campaign's input rule with the new column scores: largest/smallest total input #17/#61, largest/smallest column score #29/#20, and chain step #31 from this weight set's chain #30 end state.

Runs: maxsum #17, minsum #61, maxcol #29, mincol #20, chain #31. Devices audited: 134 (crossbar 21). **Above 3.5 V: 0** (old weights: 0 of 134).

| Rank | Device | Max \|V_G·\| (V) | Margin (V) | When (µs) | Run |
|---|---|---|---|---|---|
| 1 | X80 | 3.340 | 0.161 | 10.63 | aud_maxsum_s17 |
| 2 | XNP5 | 3.308 | 0.192 | 10.73 | aud_maxsum_s17 |
| 3 | X124 | 3.308 | 0.192 | 10.73 | aud_maxsum_s17 |
| 4 | XNP3 | 3.308 | 0.192 | 10.69 | aud_chain_s31 |
| 5 | X104 | 3.308 | 0.192 | 10.69 | aud_chain_s31 |
| 6 | XNP1 | 3.300 | 0.200 | 0.0 | aud_maxsum_s17 |
| 7 | XNP2 | 3.300 | 0.200 | 0.0 | aud_maxsum_s17 |
| 8 | XNP4 | 3.300 | 0.200 | 0.0 | aud_maxsum_s17 |
| 9 | XWR | 3.300 | 0.200 | 20.0 | aud_maxsum_s17 |
| 10 | X69 | 3.300 | 0.200 | 151.0 | aud_maxsum_s17 |

Crossbar maximum: new 2.433 V (X1) vs old 2.429 V; worst device overall old: X80 3.339 V.

- **0 of 134 TFTs exceed 3.5 V.** The worst device is again X80 (idle pull-down of `win`) at 3.340 V during reset, margin 0.16 V.
- **The crossbar maximum is 2.433 V** (old 2.429 V), at the row step into calibration. The new bank widths change the crossbar stress by only a few mV.
- rev10 `audit.py` agrees on every run (`raw/A3_FINAL_frozen/stress/*.audit.txt`).

## 7. Independent leakage audit (A4)
**How it was run.**
- An independent audit, run separately and given only the repository and DECISIONS.md, reviewed the report at commit `aa2fc18` on 2026-10-26, 22:28–23:00 UTC.
- It was told to look for any path by which test information could reach training, selection, calibration, warm starts or timing. It was also told to recompute every number in the report from the raw per-run files.
- It made no changes and ran no SPICE.

**Verdict.** No blocking issue, and no path by which test-set information reached training, selection, calibration, warm starts, hyperparameters or timing choices. Every number it recomputed from the raw runs matched (A0–A3), apart from the rounding and wording items below.

**What it checked and found clean.**
- **Script data access:** only the post-freeze scripts `eval_test.py`, `robustness.py` and `stress.py`, plus the netlist-text check `check_tooling.py`, touch test data. All 873 per-run JSONs carry inputs and labels matching their declared split.
- **Surrogate constants:** they reproduce exactly from `raw/K_old`, `raw/sens_old` and `raw/retrim_old`, and the nominal set didn't change after the S runs.
- **Data partition:** `splits.json` regenerates exactly, and S, T and K are disjoint as described.
- **Warm starts:** all are built on training sample #123.
- **Ordering:** every DECISIONS amendment was committed before the weights were frozen (705d260, 14:24:31 UTC), and every test or A3 output is later. No raw run was modified, and nothing outside this folder changed.

**Findings and what was done.** Severity is the auditor's.

| # | Severity | Finding | Fix |
|---|---|---|---|
| 1 | should-fix | **The old weights were an undeclared optimiser start** in families a–c. They had been fitted on all 210 training samples, so they had seen S and the CV validation folds. They won the training objective in some CV jobs; the final weights don't descend from them. | Declared as deviation W16.1. The CV of the three chosen configurations was re-run without that start (§4 end, `A4_no_old_start.json`). §4's statement about S was reworded. |
| 2 | minor | **Rounding:** Wilson bounds were rounded twice (90.6 vs 90.7 %); one McNemar p was printed as 0.84 in one place and 0.85 in another; medians ending in .5 were shown as integers. | One half-up rounding; 6-decimal storage; the summaries were regenerated, changing only those fields (W16.7). |
| 3 | minor | **Progress-log wording:** the A2 summary was recomputed (not "run once"); the A2/A3 start times were ≈ 3 min early; "11 dies" were 11 files covering 10 dies. | Corrected (progress log items 20, 22, 24, 26; not included in this release). |
| 4 | minor | **Unlogged deviations:** the G_res bracket rule; the integer-ceiling choice; "exact MILP" was in fact a node-limited polish; W13 cited 39/40 for the winner agreement, which was 40/40. | Logged as W16.2–W16.5; none changes a result. |
| 5 | minor | **Wording:** near-tie gap error ±2 vs ±2–4 µs; "all calibration runs use the old weights" (the unequal-sum check didn't); "calibrated on … three probes". | Reworded (§3, §8). |
| 6 | ok-but-note | **The freeze guard accepted a tracked-but-uncommitted file.** The weights were in fact committed 14 s before the first test run. | The guard now checks the content at HEAD (W16.6). |
| 7 | ok-but-note | **Every script loads the test arrays at import** and switches on a split string. | Not changed (the code that produced the results is kept). All per-run files were checked for the right split. |
| 8 | ok-but-note | **Inherited rev10 artifacts:** the lab prior is probably a test-sample end state; the old weights' selection history is unknown. | Added to §8. |
| 9 | ok-but-note | **Selection effects:** the W14 grid widening came after seeing (b)'s CV; "cand_a's S results were not opened" can't be verified. | Stated in §4 and §8. |

## 8. What this does not show
- **Not real data.** The dataset is synthetic (`clinical_validation: false`); classes and groups are generated. 90 test samples give a Wilson CI of about ±10 points, and the paired test can't resolve differences of a few samples.
- **The corner and sizing are the campaign's reconstructions** (C10-DNTT on Si, currents read by eye, JOFF/LOV not fitted, sizing rebuilt from the author's decisions). Everything here inherits that.
- **The surrogate's constants come only from old-weights runs** at one nominal corner (plus 8 runs per re-trimmed corner) and one warm-start history; the probe and candidate runs were checks, not fits.
  - It agreed with SPICE on every winner it was asked about (K, S, mismatch dies, unequal sums, test).
  - Near ties (gaps ≈ 7–12 µs) are uncertain by ±2–4 µs.
  - Re-trimmed corners have 8 runs each; at 0.95 V it agreed on 6/8 outcomes.
  - Common-mode devices (`ref`, `vls`, bias, dummy columns) aren't in its mismatch model.
- **Mismatch is assumed** (size-scaled V_th only, anchors 20–35 mV). No measured C10-DNTT mismatch exists.
- **The selection set has N = 40,** so the SPICE decision between candidates can only detect large differences. It found none.
- **Weights selected on training CV do not guarantee test gains.** Here the CV-best candidate tied the old weights on test and had lower validity.
- **The old/new comparison uses different warm starts** (#81-derived vs training-derived). The chain bounds the history effect at a few µs of gap, which is enough to flip a near tie.
- **Option (d) explored only T₁/WMIN** (V₂ offset fixed). The screening used the T₁ = 170 µs calibration for every timing, and no timing was simulated in SPICE because none won.
- **No layout parasitics, IR drop or noise.** Absolute race times are model-dependent; read ordering and gaps.
- **Inherited rev10 artifacts of unknown provenance:**
  - The lab prior `t6L_x2_v085`, which starts every warm-start chain, is probably a lab-corner end state of a test sample. It holds node voltages only, and each chain converged on training sample #123 (changes of ≈ 6.9 mV, then ≤ 0.1 mV).
  - The old weights are "the author's choice" in the lab-corner design notes, next to test-set accuracies, so how they were chosen is unknown. They are used for K selection, as the calibration weights and as one optimiser start (W16.1); the final weights don't descend from them.
- **The W14 grid widening** came after (b)'s CV was seen, and the (b) and (c) winners are W14 configurations, so their CV scores are slightly optimistic. It doesn't affect the pick (cand_a, family a).

## 9. Proposals
Each item is a proposal; none was simulated unless stated.
1. **Give the classifier a real per-class bias.** This is the largest lever left: ≈ 6 points in the A0 ceilings (67.9 % → 73–74 % in CV, float).
   - Column sums of 50–60 recover only part of it, through the C2 slope, and nothing measurable on test.
   - Two host-side ways to add a bias without touching the comparator:
     - **a seventh "bias row":** driven for a fixed host-set time in C1, whose banks set a per-class offset in the same units as the weights. It costs up to 5 banks within the 134-TFT budget.
     - **per-class host-set rail reset levels:** the campaign's proposal 5, which also removes the reset-switch V_th offset.
   - The surrogate in this folder can evaluate either before any SPICE run, since both are just extra terms in Vₖ.
2. **Treat a double latch as "undecided", not as an answer.** Near ties are now the main SPICE loss (8/90 invalid against 3/90). A host that sees two latched classes could:
   - re-run the cycle with a longer T₁ (wider C1 gap; in the surrogate screen of (d), T₁ = 200–230 µs with WMIN 20 µs keeps the re-trimmed corners up to 0.85 V at their T₁ = 170 µs level, not checked in SPICE);
   - or report "no decision".
   This trades accuracy against abstention and needs no circuit change.
3. **Select with validity in mind.** The margin objective counts training samples above G_res + m, but on the test groups the gap distribution shrank (median 85 against 102 µs). A selection score that penalises the expected number of near ties (P(gap < G_res) under the surrogate) would have favoured larger typical gaps. More data would help more than more optimisation: the CV SD over repeats (≈ 1.5 points) is as large as the differences between the top configurations.
4. **If host timing is revisited, re-trim T₁ with |V_th|.** Longer T₁ helps mismatch but fails at re-trimmed 0.95 V through trips during C1 (A1 (d) screen). T₁ should shrink as |V_th| rises, as the campaign suggested for V₁. The V₂ offset (C2 slope) is unexplored and needs its own near-tie calibration.
5. **Which weights to keep.** On this evidence the old weights are at least as good: same test accuracy, higher validity (87 against 82/90), one more correct on S. The new weights' only advantage (mismatch at the 35 mV anchor, +4 of 100) isn't significant. Unless mismatch robustness is weighted above nominal validity, I'd keep the old weights for nominal operation and treat cand_a as an equivalent alternative.
6. **Faster latch regeneration** (the campaign's proposal 7) would shrink G_res (≈ 9 µs) and is the circuit-side fix for item 2.
