# Scheme-A weight retraining: protocol and decisions

Work folder `results/weights_schemeA/`. **W1–W12 were written and committed before any training, model selection or simulation in this folder.** Later entries are dated and say whether they were made before or after seeing the data they concern.

## W0. What is frozen and what changes
- **Circuit:** Variant 3 at `fitc10`, exactly as the campaign builds it (`results/fitc10_campaign/scripts/common.py::build(variant=3)`), 2500 µs window after C2, `RELAX=1` solver set. My wrapper `scripts/wcommon.py::build` reproduces `common.build` byte for byte for the old weights (`summary/check_tooling.json`, check 1) and the campaign's stored netlist for test #31 (check 2; only the netlist text was compared, no result was read).
- **Only the finger matrix changes.** Host timing stays at the frozen protocol (T₁ 170 µs, WMIN 20 µs, GAP 5 µs, V₁ = 3.3 − |V_th| − 0.83, V₂ = 3.3 − |V_th| − 0.25), except in the separate, declared option (d) (W8).
- Nothing in `rev10/` or `results/fitc10_campaign/` is modified. They are imported; `__pycache__` writing is disabled.

## W1. Hardware constraints on the weights (checked in code and the lab-corner design notes, now [docs/TOOLING.md](../../docs/TOOLING.md))
1. **Integer fingers**, F[i, k] ≥ 0 (row i = input, column k = class). Bank (i, k) is one `potftseg` instance, W = 10 µm × F[i, k], L = 54 µm.
2. **Per-column budget: Σᵢ F[i, k] = 60 for every class k.** The current weights use exactly 60 per column, `rev10/eval/hw_retrain.py` asserts it, the lab-corner design notes say "60 fingers per column". I keep it as an equality, not "≤ 60": scheme A relies on all columns having the same C2 slope (the race is then decided only by the C1 charge), and the surrogate is calibrated only on equal columns.
3. **TFT count ≤ 134.** Non-crossbar TFTs: 113. Each non-empty bank adds one instance, so the count is 113 + (number of non-empty banks) ≤ 134 → **at most 21 non-empty banks** (the current weights have 21; 9 empty).
4. **At least 15 non-empty banks.** Not a design rule but a tooling fact found on 2026-10-25 before training: the frozen builder `rev10/sim/tools/build_A.py` asserts `n >= 15` crossbar instances. Since rev10 can't be modified, 15 ≤ non-empty banks ≤ 21.
5. Sign and offset: the crossbar has no negative weights and no bias. Adding the same amount to every class in a row is invisible to the race (only differences between rails matter), so non-negativity alone costs nothing. The binding constraints are **equal column sums and no per-class bias** (the WMIN pedestal adds the same 60·WMIN finger-µs to every class). The A0 ceilings separate these effects.

## W2. Data partition (fixed by `scripts/splits.py`, seeded, before any training)
- **Test set (90 samples): sealed.** No training, selection, calibration or timing script reads `X_test`/`y_test`. The test set is used once, for the final weights (W10), and that result is reported whatever it is. Previous campaign SPICE results on test samples are not used to tune anything (W12).
- The 210 training samples come in 21 acquisition groups of 10 (2 per class). The train/test split is by group, so **all CV inside the training set is group k-fold.**
- **Selection set S:** 4 of the 21 training groups (40 samples, 8 per class), drawn with `default_rng(20261025)`. S is held out from **candidate training and from calibration**. It is used only for (i) the SPICE decision between the top candidates (W9) and (ii) reporting the calibrated surrogate's agreement with SPICE on held-out samples.
- **Training pool T:** the other 17 groups (170 samples). Candidates are trained and cross-validated on T.
- **Calibration set K ⊂ T:** 40 samples, 8 per class. Within each class (34 candidates in T), samples are ranked by the old weights' software score margin m = s_y − max_{j≠y} s_j (s = x·F, finger units): the 3 with the smallest |m| (near ties, either sign, to locate the resolve threshold), then 5 at the 10/30/50/70/90 % quantiles of m among the rest. Only training labels and the old weights are used.
- **CV on T:** 17 groups, 5 folds (4/4/3/3/3 groups), 4 repeats with `default_rng(1000 + r)` group permutations → 20 train/validation splits.
- **CV for the A0 ceilings:** all 210 training samples, 21 groups, 5 folds (5/4/4/4/4 groups), 10 repeats with `default_rng(2000 + r)`. Ceilings are reported, not used for selection.

## W3. A0 software ceilings (on training data only)
Accuracy = argmax of the linear score, no circuit. Group 5-fold CV × 10 repeats on the 210 training samples; hyperparameters (regularisation) are chosen by an inner group CV on each outer training fold (nested), so the outer numbers aren't tuned on their own folds.
1. **Best float linear classifier**, with per-class bias, no constraints: multinomial logistic regression and a linear SVM (one-vs-rest and Crammer-Singer); the best of the methods is reported as the ceiling, all are listed.
2. **Best non-negative linear classifier as the crossbar sees it:** W ≥ 0, no bias, equal column sums (scale-free). Trained as multinomial logistic regression with these constraints. Also reported: non-negative with bias, and non-negative without the equal-sum constraint, to show which constraint costs what.
3. **Best integer-finger classifier:** W1 constraints (integer, column sums 60, 15–21 non-empty banks). Trained by MILP (HiGHS) maximising the number of training samples with a positive score margin, and by rounding + local search from the constrained float solution; the better of the two in inner CV is used per outer fold.
- The old weights are listed for reference; their numbers on training folds are **in-sample** (they were trained on all 210).

## W4. Surrogate and its calibration (A0)
**Model** (`scripts/surrogate.py`). For class k with C1 drive Dₖ = Σᵢ F[i,k]·(WMIN + xᵢ·T₁) (finger·µs):
- rail at C2 start: Vₖ = Rₖ + α·Σᵢ F[i,k]·g1[i,k]·(WMIN + xᵢ·T₁ − δ) (+ a quadratic term in Dₖ only if the calibration residuals call for it);
- C2 slope: σₖ = γ·Σᵢ F[i,k]·g2[i,k];
- trip time from C2 start: tₖ = (Θₖ − Vₖ)/σₖ + τ (if Vₖ ≥ Θₖ before C2, the trip time inside C1 is solved from the piecewise-linear C1 schedule; **a trip during C1 counts as a failure**, the campaign's "strict" reading);
- winner = first trip; **runner-up gap** = t₍₂₎ − t₍₁₎; **correct ⇔ winner = label and gap ≥ G_res** (resolve threshold). Below G_res the run is a near tie and counts as wrong.
- Nominal die: g1 = g2 = 1, Rₖ, Θₖ per class from calibration (history can give small per-class offsets).

**Calibration runs** (old weights, nominal `fitc10`, frozen timing; warm start per W6):
1. **K, 40 runs.** Fit α, δ (from the rail at C2 start vs Dₖ for all 5 rails), γ (C2 slopes), Θₖ and τ (winner's trip), the **gap scale** (SPICE gap / surrogate gap, and SPICE gap / the lab-calibrated `rev10/eval/schemeA.py` gap for comparison with the campaign's 0.84), **lock latency** (distribution), **resolve threshold** G_res (logistic fit of valid vs SPICE gap; G_res = the 50 % point) and the **near-tie failure behaviour** (failure types, which classes latch).
2. **Held-out agreement:** (i) 5-fold CV inside K (fit on 32, predict 8); (ii) old weights on the 40 S samples, predicted by the surrogate frozen after step 1. Reported: winner agreement, correct/incorrect agreement, validity agreement, gap correlation and ratio. If the surrogate is changed after (ii), that change is declared and (ii) is no longer an independent number.
3. **Mismatch injection** (for candidates b–d): one-device V_th perturbations on one K sample with a large gap: +30 mV on the winner's reset switch (X75+k), sense device (X81+10k), detect load (X82+10k), trip driver (X83+10k), latch devices (X84–X87+10k), and on one crossbar bank of the winner's column; −30 mV on the sense device and the reset switch (linearity). ≈ 11 runs. They give the coefficients by which each device's ΔV_th moves Θₖ, Rₖ, g1, g2. Common-mode devices (`ref`, `vls`, bias, dummy columns) are not modelled (they shift every class alike).
4. **Mismatch check:** 3 analytic-paired dies (size-scaled V_th only, anchor 35 mV, `apply_mc_paired` with seeds 35101–35103) × 10 K samples = 30 runs; report per-die/sample winner agreement between the surrogate (fed the same draws) and SPICE.
5. **Re-trim calibration** (for c–d): 8 K samples (2 at the largest, 2 at the smallest max-column score, 4 spread) at re-trimmed |V_th| 0.55, 0.75, 0.85, 0.95 V (corners `fc10_vthXXX`, levels by build_A's formula) = 32 runs → per-|V_th| Rₖ, Θ, α, γ, τ, and trips in C1. 0.65 V comes from step 1.
- All calibration samples are training samples in K. Step 2(ii) is the only use of S before W9.

## W5. Analytic Monte Carlo dies (for b–d and the CV metrics)
- **Size-scaled V_th only**, the campaign's 3B-V convention: σ = anchor·√(780 µm²/(W·L)) per instance, µ and R_C nominal. A bank has W·L = 540·F[i,k] µm². Anchors **20 and 35 mV**, half of the dies each.
- Each die has one z-score per bank position (i, k) and per class-chain device; σ follows the bank's area for the weights being evaluated (common random numbers across candidate weights, as `apply_mc_paired` does in SPICE).
- **Training dies** (inside optimisers): seeds 31000+, 64 per anchor. **Evaluation dies** (CV metrics): seeds 41000+, 250 per anchor. Disjoint.

## W6. Warm starts
- The campaign's `fitc10` warm start was built from test sample #81. **I don't use it.** Each weight set gets its own warm start by the campaign's D7 procedure (chained runs from the borrowed lab prior `t6L_x2_v085`, until every rail reset level moves < 5 mV, at most 6 runs), on a **training sample**: the class-5 sample in T with the largest software margin under that weight set, so that the history matches the campaign's ("class 5 won").
- Consequence for the paired comparison with the old weights on the test set (W10): the old Phase 1 used the #81-derived warm start, the new weights use a training-derived one. The campaign's chain test bounds the history effect at a few µs of gap; I report this as a confound.

## W7. Candidates (A1), all trained on T only
- **(a) Margin-maximising.** Maximise the number of T samples whose correct class wins with gap ≥ G_res + m, on the nominal calibrated surrogate. With equal column sums and no C1 trips at 0.65 V this is linear in F, so it's solved as an **exact MILP** (HiGHS; big-M per sample; bank binaries for W1.3–4; time limit per solve, incumbent and MIP gap recorded). Margin grid m ∈ {0, 5, 10, 20, 30, 45, 60} µs, chosen by CV.
- **(b) Mismatch-aware.** Maximise the expected accuracy over the training dies (W5, anchors 20/35 mV), noise injected per W4.3. Smoothed objective mean σ((min_{j≠y}(tⱼ − t_y) − G_res)/τ) with τ ∈ {0 (exact count), 2, 5} µs chosen by CV. Optimiser: simulated annealing over integer moves (move 1–3 fingers between two rows of a column; banks may empty or open within 15–21), then greedy descent to a local optimum; starts from the (a) solutions and from the rounded constrained-float solution; best of 3 restarts on the training objective.
- **(c) Re-trim-aware.** (b) averaged uniformly over re-trimmed |V_th| ∈ {0.55, 0.65, 0.75, 0.85, 0.95} V with the W4.5 parameters.
- **(d) Optional, declared: (c) + host timing.** Search space T₁ ∈ [120, 300] µs, WMIN ∈ [10, 40] µs, V₂ offset ∈ {0.20, 0.25, 0.30} V; GAP 5 µs and V₁ offset 0.83 V fixed (V₁ also sets the `ref` calibration charge, which the surrogate doesn't model). A timing candidate is only taken to the SPICE check after its timing has been calibrated on K samples in SPICE (same procedure as W4.1, ≥ 16 runs). Reported separately from the frozen-timing result, always next to it.
- Also evaluated as references (not candidates): the old weights (in-sample on T), and the A0 integer-ceiling weights refit on T.
- Every optimiser setting tried is recorded in `summary/A1_*.json`.

## W8. CV selection metric (on T, surrogate only)
For each candidate configuration, trained on the 4/5 training part of each of the 20 splits and evaluated on its validation part:
- A_nom: nominal-die accuracy at 0.65 V, frozen timing;
- A_mm: mean accuracy over the 500 evaluation dies (W5) at 0.65 V;
- A_rt: mean nominal-die accuracy over re-trimmed |V_th| {0.55, 0.65, 0.75, 0.85, 0.95} V (strict: trips in C1 fail).
- **Score S = 0.5·A_nom + 0.25·A_mm + 0.25·A_rt.** Within each family the configuration with the highest mean S is chosen and then retrained on all of T. The S value, its spread over splits, and each component are reported.

## W9. SPICE selection on S (decides the winner)
- Candidates: the best configuration of each of (a), (b), (c) (3 candidates; if two are the identical matrix, the next-best configuration of the later family takes its place). Each gets its W6 warm start, then 40 nominal runs on S. The old weights are also run on S (reference only, not a candidate).
- **Winner = highest SPICE accuracy on S** (invalid = wrong). Tie → higher CV score S. The winner's matrix, as trained on T, is the final frozen-timing weight set: **no refit on all 210 samples**, so the matrix that reaches the test set is the one checked in SPICE.
- Option (d), if run: its best timing candidate is run on S at its timing (own warm start) and becomes the co-optimised-timing set only if its S accuracy is ≥ the frozen-timing winner's; otherwise it's reported and not taken to the test set.
- Weights are frozen and committed (`weights/FINAL_*.npy`, with sha256) before any test-set run.

## W10. Test-set evaluation (A2, run once)
For the final set(s): all 90 test samples, nominal `fitc10`, own warm start; the campaign's chain (test 30–39 in sequence). Reported: accuracy (Wilson 95 %), validity, confusion matrix, gap distribution, lock latency, surrogate agreement (surrogate predictions on the test set are computed only after the weights are frozen), and a **paired comparison with the old weights' Phase 1 (Variant 3) per sample: exact two-sided McNemar test** on discordant pairs. Whatever the result, it's reported; nothing is re-selected after it.

## W11. Robustness and stress (A3), final weights only
- Same 20-sample subset as the campaign (`summary/phase3_subset.json`), same corners and settings:
  - fixed-level |V_th| 0.45–1.05 V and µ ×0.5/×0.75/×1.25 (3A), re-trimmed |V_th| 0.75–1.05 V (3A-T); the nominal point is the A2 runs of those 20 samples;
  - 3B-V: size-scaled V_th only, anchors 20 and 35 mV, 5 dies each, **the same seeds** (1000·anchor + die), draws paired by `apply_mc_paired` (identical z-score per instance; banks get σ from their own area; banks that are new in the new weights get z from a separate seeded stream).
- Paired comparison with the old weights' results on the same samples/dies.
- **Phase 2 stress audit:** 5 runs chosen by the campaign's input rule (`phase2_audit.pick`, evaluated with the new weights' column scores) incl. chain step #31 from the chain #30 end state; every TFT, crossbar included; limit 3.5 V.
- The warm start for every A3 point is the nominal one (as in the campaign).

## W12. Honesty and leakage rules
- I read the campaign's REPORT.md, which contains test-set-derived summaries (SPICE/model gap ratio 0.84, near-tie boundary 7.9–10.7 µs, lock latency ≈ 19 µs, ≈ 870 µs races). **None of these numbers is an input to any script here;** every constant is re-fit from training-sample runs. Scripts read campaign files only for: the tooling equality check (`check_tooling.py`: one stored netlist and one stored draws file), the Phase 3 subset definition and the old per-run results for the paired comparisons (only in A2/A3 scripts, after the weights are frozen).
- No "verified"/"validated". Every number is reproducible from committed scripts; failures are reported as failures; the report has a "what this does not show" section.
- An independent audit, run separately with access only to the repository and this file, checks leakage and numbers (A4); its findings and the fixes go into the report.
- Waveforms (`*.csv.gz`), netlists (`*.cir.gz`) and draws (`*_draws.json`) under `raw/` go to Git LFS. *(Public release: these files are not included; they can be regenerated by re-running the campaign, see [REPRODUCE.md](../../REPRODUCE.md) §6.)*

## W13. Amendment: column sums 50–60 as a CV-selected option (2026-10-25, after the K calibration and the A0 interim ceilings, BEFORE any candidate training)
- **Why.** (1) The campaign specification's "per-column finger budget" is a cap, so Σᵢ F[i,k] ≤ 60 is within it; W1.2's "= 60" was my stricter reading. (2) Unequal sums give the race a per-class bias. With nₖ = Σᵢ F[i,k] and the calibrated model, tₖ = (Θ − R − c₀)/(γ nₖ) − α·WMIN/γ − (α T₁/γ)·(sₖ/nₖ): the pedestal term is common, but the distance-to-threshold term (Θ − R − c₀)/(γ nₖ) is a bias that grows as nₖ shrinks. (3) Training-data evidence, seen before this amendment: the interim A0 ceilings (11 of 50 splits) put a float linear classifier with bias ≈ 4–5 points above the bias-free, equal-sum form; a probe on the 20 CV splits of T (`scripts/colsum_probe.py` → `summary/A1_colsum_probe.json`, nominal surrogate, greedy descent from the rounded LR) gave 67.5 / 69.0 % (m = 0 / 20 µs) with sums fixed at 60 against 69.9 / 70.0 % with sums free in [45, 60]; the chosen sums were 56–60.
- **Rule.** Every family gets a "column-sum mode" hyperparameter: `eq60` (Σ = 60, as pre-registered) or `le60` (50 ≤ Σ ≤ 60). CV (W8) chooses per family. For family (a) the MILP polish only exists for `eq60`; `le60` uses the same local search without it. The 15–21 bank rule and everything else are unchanged.
- **Lower bound 50:** the C2 slope scales with nₖ, so a 50-finger class races 1.2× longer. Races then still fit the 2500 µs window at nominal (≈ 1.1 ms max × 1.2), but the fixed-level |V_th| = 0.75 V drift point (old weights: races up to ≈ 2.4 ms) can time out. This is a known trade-off; A3 measures it.
- **Surrogate check for unequal sums** (the calibration has only equal columns): the probe procedure (le60, m = 20 µs) is trained on all of T → `weights/probe_le60.npy`; it gets its own W6 warm start and 20 SPICE runs on K samples (per class: the 2 smallest predicted gaps and the 30 %/70 % gap quantiles under that matrix). Reported like W4.2. Physically the per-finger currents and the rail capacitance (2201 pF CRAIL vs ≈ 0.14 pF overlap per finger) barely depend on nₖ, so the model should transfer; this checks it. If the check fails (winner agreement below the K calibration's 39/40 by more than 2), `le60` is dropped.
- Config tie-break in W8 (recorded here, it's in `cv_eval.py`): equal S → the smaller config value.

## W14. Amendment: wider regularisation grid for (b) and (c) (2026-10-25 ≈ 20:30 UTC, after seeing the CV results of (a) and (b), BEFORE training (c))
- **Seen (training CV only):** (b) reached ≈ 72.5 % expected accuracy over its training dies on its own training samples, but ≈ 63–64 % over the evaluation dies on the validation folds; (a) with a 30 µs margin generalised better (≈ 66 %). The declared smoothing τ ∈ {0, 2, 5} µs is small next to the mismatch-induced timing noise (≈ 25 µs per class at the 20–35 mV anchors), so the annealer fits individual training samples.
- **Change:** the (b)/(c) objective becomes mean over dies of σ((M − m)/τ) (step for τ = 0), and the grid gets four more (τ, m) configurations: (10, 0), (20, 0), (5, 15), (5, 30) µs, in both column-sum modes. The original three (τ = 0/2/5, m = 0) stay. Selection is still by the W8 CV score; all configurations are reported.
- Nothing else changes (starts, annealing schedule, dies, splits).

## W15. Option (d), co-optimised host timing: procedure (2026-10-25 ≈ 21:05 UTC, declared before any (d) run; (c) training still running)
- **Search space, narrowed from W7:** T₁ ∈ {170, 200, 230, 260} µs × WMIN ∈ {20, 40} µs. V₂ offset fixed at 0.25 V (not 0.20/0.30): changing the C2 slope would change G_res and the effective trip levels, which are calibrated only at 0.25 V and would need their own near-tie runs. V₁ offset 0.83 V and GAP 5 µs fixed as in W7. Reason for expecting a lever (surrogate only, old weights on T): raising T₁ widens the C1 voltage gap between classes relative to the mismatch-induced trip-level offsets and shortens the C2 distance over which slope mismatch acts; the limit is trips during C1, worst at high re-trimmed |V_th|.
- **Weights configuration:** the (c) family's CV-best (mode, config) from `summary/A1_cv.json`, trained by the (c) procedure with the surrogate evaluated at the timing (per-finger parameters, trip levels, G_res and the re-trim corners are the T₁ = 170 µs calibration; the C1 drive and the C1-trip check follow the timing).
- **Screening:** all 8 timings on the 5 splits of CV repeat 0 (paired across timings), S at that timing (W8 definition). Best mean S wins; ties → the frozen timing, then the smaller T₁. If the frozen timing wins, (d) stops there and is reported as "no better timing found".
- **Otherwise:** (1) full 20-split CV of the chosen timing, reported; (2) `cand_d` = that configuration trained on all of T at the chosen timing; (3) its own W6 warm start at that timing; (4) SPICE check of the surrogate at that timing on 20 K samples (selection rule of the W13 check, under `cand_d`): if winner agreement is < 17/20, (d) is dropped; (5) 40 S runs at that timing. Per W9, `cand_d` becomes the co-optimised-timing set only if its SPICE accuracy on S is ≥ the frozen-timing winner's.

## W16. Deviations found by the independent audit (A4), recorded 2026-10-26 ≈ 23:05 UTC, AFTER the test-set results
None of these changes a result; each is a place where the code didn't do exactly what W1–W15 say, or where W1–W15 left something unstated.
1. **The old weights were an undeclared optimiser start** in all families (`train.py` starts for a and b/c, `timing.py`).
   - They were fitted on all 210 training samples, so they had seen S and every CV validation fold.
   - They won the training objective in some CV jobs, including 3/20, 3/20 and 7/20 splits of the chosen a/b/c configurations.
   - None of the final candidates descends from them: cand_a's (a) run and the a_m20 start used by cand_b/cand_c all won from the `lr0.001` start.
   - The CV of the three chosen configurations was re-run without that start (`scripts/no_old_start.py` → `summary/A4_no_old_start.json`) and is reported next to the original; the family ranking a > b > c, which decided the W9 tie-break, is unchanged.
   - S was never used to *fit* anything, but the statement "S held out from all training" is only true if the old weights' own history (rev10, all 210 samples) is excluded.
2. **G_res rule:** W4.1 says "logistic fit, G_res = the 50 % point". `calib_fit.py` uses the midpoint of the clean bracket when valid/invalid separate (8.70 µs) and the logistic point only otherwise (8.65 µs here). Difference 0.05 µs.
3. **Integer ceiling (W3.3):** both the local-search and the MILP-polished integer rows are reported. Neither was chosen per fold by inner CV as W3.3 says (68.1 % and 68.0 %).
4. **"Exact MILP" for (a) (W7):** in practice greedy integer descent, then a MILP polish with a 3000-node budget (all 140 solves stopped at the node limit, median gap 25 %), and none for column sums 50–60 (as W13 says). The incumbents are not proven optimal.
5. **W13 threshold:** W13 cites "winner agreement 39/40" for K. The current K fit had 40/40 winners (39/40 was its validity agreement). With 40/40 the rule reads "drop le60 if fewer than 18/20 winners agree"; the check had 20/20, so the decision is unchanged.
6. **The freeze guard** (`eval_test.frozen`) only checked that the weights file was tracked by git, which a staged file also passes.
   - The weights *were* committed first: 705d260 at 14:24:31 UTC, with the same SHA-256; the first test run started ≈ 14 s later.
   - The guard now checks the file's content at HEAD (hardening after the fact; it doesn't change any run).
7. **Rounding:** Wilson bounds were stored at 4 decimals and rounded again for display; medians ending in .5 were printed as integers.
   - Now: 6 decimals stored, one half-up rounding for display.
   - `summary/A1_select.json`, `A2_FINAL_frozen.json` and `A3_FINAL_frozen.json` were regenerated. Only the `wilson95`/`strict_wilson95`/`mcnemar_exact_p` fields changed, by ≤ 6e-5.
