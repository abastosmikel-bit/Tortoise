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

{{TABLE:CEILINGS}}

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

{{TABLE:CALIBRATION}}

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

{{TABLE:A1_CV}}

**Reading of the CV.**
- **Margin maximisation (a) beats the mismatch-aware objectives (b, c) even on their own mismatch and re-trim components.** The annealer fits individual training samples and dies; a plain margin regularises better with 130–140 training samples per split.
- **Unequal column sums help every family by 1–3 points of S.**
- **The best candidate's CV score equals the old weights' training-set score** (0.691 both). The old weights' figure is in-sample and therefore optimistic, so a small CV gain over them is plausible, but it isn't resolvable.

**SPICE decision on S (W9).** The best configuration of each family was retrained on all of T, given its own warm start, and run in SPICE on the 40 held-out S samples. The rule: highest SPICE accuracy wins, ties go to the higher CV score. The old weights are run as a reference only. Source: [A1_select.json](summary/A1_select.json).

{{TABLE:A1_SELECT}}

- **The three candidates tie at 25/40,** so the CV score picks **cand_a** (family a, column sums 50–60, m = 30 µs). It was frozen with its SHA-256 and committed (`705d260`) before any test-set run. Its column sums are 58/60/60/60/59, with 21 non-empty banks (134 TFTs, the same as now).
- **On S the old weights score 26/40,** one more than every candidate; with N = 40 that difference is noise. **The selection step found no evidence that any candidate beats the old weights.**
- **The surrogate called every winner in all 160 S runs.**
- **Order of S runs:** cand_a's S runs ran before (b)/(c) finished, and by my log their results were not opened until all three candidates were frozen. Four lines of cand_b's log were seen while checking CPU load (progress log items 13 and 16; not included in this release).
  - The audit notes that the first claim can't be verified from the record (the run log was committed).
  - There was also no channel through which the S results could have mattered: W14 was committed before those S runs, and (b)/(c) ran unattended from fixed grids.

**Sensitivity to the undeclared old-weights start (audit finding 1, W16.1).**
- The old weights were one of the optimiser starts in every family, and they had been fitted on all 210 training samples.
- The CV of the three chosen configurations was re-run without that start; everything else (splits, seeds, dies) is unchanged. Source: [A4_no_old_start.json](summary/A4_no_old_start.json), `scripts/no_old_start.py`.

{{TABLE:NO_OLD}}

- **Result:** without the old-weights start the three chosen configurations score S = 0.694 (a), 0.681 (b) and 0.668 (c), against 0.691, 0.674 and 0.673 as run. The weights changed in 3, 3 and 7 of the 20 splits.
- **The order a > b > c is unchanged,** and with it the W9 tie-break that picked cand_a.
- **Not re-run:** whether some other configuration would have overtaken the chosen one within a family; that would repeat all of A1.
- **No final candidate descends from the old weights:** cand_a's run and the a_m20 start used by cand_b/cand_c all won from the `lr0.001` start.

## 5. Test-set results compared with the old weights (A2, run once)
The frozen weights were run once on all 90 test samples, nominal `fitc10`, own warm start, plus the campaign's 10-sample chain. The old weights' per-sample results are the campaign's Variant 3 Phase 1 runs, which used the #81-derived warm start; the different warm starts are a confound of a few µs of gap (chain below). Sources: [A2_FINAL_frozen.json](summary/A2_FINAL_frozen.json), [A2_FINAL_frozen_runs.csv](summary/A2_FINAL_frozen_runs.csv), `scripts/eval_test.py`.

{{TABLE:A2}}

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

{{TABLE:A3}}

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

{{TABLE:STRESS}}

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
