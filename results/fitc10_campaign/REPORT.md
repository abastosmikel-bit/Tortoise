# Tortoise at the C10-DNTT corner (`fitc10`): SPICE campaign report

**Status: complete (2026-10-22; follow-ups 3A-T, 3B-P and 3B-V added 2026-10-25).** Main design: Variant 3. Variant 1 is reported as a CREF sensitivity result (§3.6). Every number links to the file it comes from. Summaries are recomputed from the raw per-run JSONs by `scripts/summarize.py` and `scripts/compare_variants.py`, or written by the phase script named.

## 1. Summary
- **Nominal accuracy:** 62/90 = **68.9 %** (Wilson 95 % CI 58.7–77.5 %); validity 87/90 = 96.7 % (90.7–98.9 %). Basis: Variant 3, `fitc10` nominal die, synthetic test set, HW-trained weights (software ceiling 70.0 %). Source: [v3/phase1.json](summary/v3/phase1.json).
- **Stress:** **0 of 134 TFTs above 3.5 V** in 5 extreme runs. Worst: X80 at 3.34 V (margin 0.16 V, during reset). The crossbar maximum is 2.43 V, above the old ≈ 2.3 V analytic bound. Source: [v3/phase2_audit.json](summary/v3/phase2_audit.json).
- **Corner window** (N = 20 per point):
  - **Drift budget, host levels fixed:** |V_th| 0.55–0.75 V (65–75 %), µ ×0.75–×1.25 (70–75 %); 0 % at 0.45 V and ≥ 0.85 V.
  - **Process window, host levels re-trimmed:** 70 % at 0.85 V, 60 % at 0.95 V, and 35 % at 1.05 V (counting trips during integration as failures).
  - Sources: [v3/phase3A.json](summary/v3/phase3A.json), [v3/phase3A_T.json](summary/v3/phase3A_T.json).
- **Assumed local mismatch** (5 dies × 20 samples per level; 75 % with no mismatch):
  - **Flat σ (worst-case bound):** median die **40 / 40 / 30 %** at 20 / 40 / 80 mV; validity ≥ 90 %; dies biased toward 1–2 classes.
  - **Size-scaled V_th only** (σ_Vth = anchor·√(780/WL), µ and R_C nominal): pooled **64 / 57 %** at anchors 20 / 35 mV (Wilson 54–73 / 47–66 %); validity 95 / 94 %; only near-tie failures.
  - The 3B-P run that also scaled µ/R_C (4–21 %) is an unphysical upper bound (§3.5b).
  - Sources: [v3/phase3B.json](summary/v3/phase3B.json), [v3/phase3B_V.json](summary/v3/phase3B_V.json), [v3/phase3B_P.json](summary/v3/phase3B_P.json).
- **CREF sensitivity** (Variant 1, CREF 24 pF): the median race goes from 870 to 1300 µs, with **90/90 identical outcomes**. The larger CREF of Variant 3 moves the upper end of the working |V_th| range from 0.65 to 0.75 V (N = 20). Source: [v1_vs_v3.json](summary/v1_vs_v3.json).

## 2. Setup
- **Code.** The frozen base-design tooling in `rev10/` (lab-corner bundle, unchanged; [docs/TOOLING.md](../../docs/TOOLING.md)). ngspice-42, 4 cores.
- **Corner.** `rev10/sim/models/fitc10.lib`, a **reconstruction** from the campaign specification: MU 5.87 cm²/Vs, VTH0 0.65 V, SS 112 mV/dec, RCW 490 Ω·cm, CI 0.70 µF/cm². **JOFF 1e-14 A/µm and LOV 2 µm are kept at the lab values (assumption).**
- **Sizing.** The lost `fitc10` netlist was **rebuilt from the author's decisions** ([DECISIONS.md](DECISIONS.md)). These are decisions, not recovered facts.
  - **Variant 3, main design (D9, adopted in D11):**
    - frozen base-design build (`build_A.py`, `VTH=065`, base `t5L_x2_v065.cir`);
    - CRAIL1–5 375 → 2201.25 pF; **CREF 24 → 140.88 pF**;
    - L ×6, W unchanged, on all 19 TFTs with drain = 0 and gate = 0 (list in D4);
    - row levels V₁ 1.82 V, V₂ 2.40 V;
    - 134 TFTs, of which 21 are crossbar instances (`potftseg`) carrying 300 fingers.
  - **Variant 1:** the same with CREF 24 pF (§3.6).
  - **Variant 2:** the Gate B fallback only.
  - **How Variant 3 was adopted (D11).** It was the author's decision **after** the Variant 1 and Variant 3 Gate B data were seen. The earlier pre-set criterion "`ref` settled at end of sampling" was withdrawn as wrong, because the lab-corner reference design doesn't settle either. It was replaced by "race time consistent with the original ≈ 800 µs".
- **Weights.** `rev10/eval/F_hw_m4_firstpass.npy` (HW-trained; trained for the old pulse law, not scheme A).
- **Protocol.** Scheme A as in the base design ([docs/TOOLING.md](../../docs/TOOLING.md) §2): T₁ = 170 µs, C2 starts at 507.5 µs.
- **Window.** `.tran 100n 3008u`, i.e. 2500 µs after C2 starts. This was raised from the 1200 µs I first fixed, after Variant 1 ran out of window (D6 amendment).
- **Solver.** The lab-corner `RELAX=1` solver set ([docs/TOOLING.md](../../docs/TOOLING.md) §6). No other simulation setting changed.
- **Warm start.** Each variant has its own `fitc10`-native warm start, from chained #81 runs starting at the borrowed lab prior `t6L_x2_v085`. Both converged in 2 runs: the largest change in rail reset level was 3.5 mV for Variant 3 and 3.7 mV for Variant 1, under the 5 mV criterion. Sources: [v3/warmstart.json](summary/v3/warmstart.json), [warmstart.json](summary/warmstart.json).
- **Definitions** (`scripts/common.py::metrics`):
  - **Trip:** a class's `na` crosses 1.65 V after 320 µs.
  - **Valid:** exactly one class has `na` > 2.5 V at the end, and it is the first tripper.
  - **Lock latency:** `win` crosses 2.05 V, minus the first trip.
  - **Runner-up gap:** time until the runner-up's rail reaches the level the winner's rail had at its trip. The rails keep charging after the lock. A slope-extrapolated value agrees within 0.05 µs for gaps under 20 µs.
- **Data storage.** During the campaign, waveforms, netlists and MC draws under `raw/` were stored in Git LFS (1891 files, ≈ 87 MB); they are **not included in this public release** (see [raw/README.md](raw/README.md)). Per-run metric JSONs, summaries and scripts are included.
- **Analytic model.** `rev10/eval/schemeA.py`, nominal die, **as-is at its lab calibration** (VTH 0.85 V, V₂ 2.20 V). Source: [analytic.csv](summary/analytic.csv).

## 3. Results

### 3.1 Phase 0: Gate B
Criteria were fixed before running (D6). #81: valid, class 5, no trip during integration, lock latency 15–25 µs. #31: valid, class 2. Both used the borrowed prior.

| Variant (window after C2) | #81 | #31 | Result | Source |
|---|---|---|---|---|
| V1, 1200 µs | trips at 1706.8 µs, not latched (race unfinished) | no trip | fail | [gateB_v1.json](summary/gateB_v1.json) |
| V2, 1200 µs | timeout | timeout | fail | [gateB_v2.json](summary/gateB_v2.json) |
| V1, 2500 µs | valid, 5; lock 18.6 µs; race 1199 µs | valid, 2; lock 17.5 µs; race 1254 µs | Gate B pass; race ≈ 1.5× original | [diag_window_v1.json](summary/diag_window_v1.json) |
| **V3, 2500 µs** | valid, 5; lock **19.8 µs**; race **773 µs** | valid, 2; lock 19.4 µs; race **831 µs** | Gate B pass; race consistent with ≈ 800 µs (D11) | [gateB_v3.json](summary/gateB_v3.json) |

- **Window change.** It only adds observation time: #81's trip is identical (1706.833 µs) at 1200 and 2500 µs.
- **What a Gate B match means.** Variant 3 is a **rebuilt design that matches the gate samples** on class, validity, lock latency (≈ 20 µs) and race time (≈ 800 µs). It is a check of the rebuilt sizing, not a reproduction of the lost runs.
- **`ref` level.** Variant 3's `ref` ends sampling at 1.38–1.39 V and is still ramping (73 mV over 308–309 µs). For comparison: lab corner 1.78 V (131 mV), Variant 1 2.41 V (171 mV).

### 3.2 Phase 1: SPICE accuracy, 90 test samples (Variant 3)
Source: [v3/phase1.json](summary/v3/phase1.json); per sample: [v3/phase1_runs.csv](summary/v3/phase1_runs.csv).

| Measure | Value |
|---|---|
| SPICE accuracy (invalid = wrong) | 62/90 = **68.9 %** (Wilson 95 %: 58.7–77.5 %) |
| Validity | 87/90 = **96.7 %** (90.7–98.9 %) |
| Failure types | multi-latched 3 (#24 → {1,2}; #25 → {2,3,4}; #42 → {4,5}); none-latched / timeout / trip during integration: 0 |
| Software argmax / scheme-A model winner, same samples | 70.0 % / 70.0 % |
| SPICE vs model winner | 87/90 agree; the 3 disagreements are the 3 invalid runs |
| Model gap vs SPICE gap (87 valid) | Pearson r = 0.9999; SPICE ≈ 0.84 × model |
| Race time from C2 start | median 870 µs, range 493–1148 µs |
| Lock latency (valid runs) | median 19.2 µs, range 19.1–20.0 µs |
| #81 / #31 (native warm start) | valid 5, race 769 µs, lock 20.0 µs / valid 2, race 826 µs, gap 10.7 µs |

Confusion matrix (rows = label; columns = SPICE class, then invalid):

| label \ SPICE | 1 | 2 | 3 | 4 | 5 | invalid |
|---|---|---|---|---|---|---|
| 1 | 16 | 1 | 0 | 0 | 0 | 1 |
| 2 | 3 | 15 | 0 | 0 | 0 | 0 |
| 3 | 6 | 2 | 5 | 2 | 1 | 2 |
| 4 | 1 | 2 | 1 | 8 | 6 | 0 |
| 5 | 0 | 0 | 0 | 0 | 18 | 0 |

**Runner-up gap vs lock latency.** This is the margin that failed at high V_th. Over the 87 valid runs:
- **Gap:** median 102 µs, 5th percentile 27.4 µs, minimum 10.7 µs.
- **Gap − latency:** median 82.8 µs, minimum −8.9 µs.
- **Below the lock latency but still valid:** 4 runs (#31 10.7, #37 10.9, #17 11.6, #3 19.3 µs). In each, a second class crossed the trip level before the lock but didn't latch.
- **Failures:** the 3 invalid runs had gaps of 1.4, 4.4 and 7.9 µs.
- **The boundary** therefore lies between 7.9 and 10.7 µs of gap, i.e. between a model gap of 9.3 µs (fail) and 12.7 µs (pass). It's set by the score margin and the slow latch regeneration (`na` takes ≈ 25 µs from 1.4 to 3.1 V), not by lock latency alone.

**History dependence** (samples 30–39 chained, each starting from the previous run's end state after the normal host reset). Source: [v3/chain.json](summary/v3/chain.json).
- **Outcomes:** 10/10 match the independent runs. Accuracy on the 10 is 9/10 either way; #37 (label 4) is classified 1 in both.
- **The first step (#30)** starts from the same state as its independent run, so 9 comparisons carry information.
- **Largest differences:** first-trip time 4.1 µs; runner-up gap 3.9 µs; rail reset level 5.5 mV; `ref` reset level 0.13 mV.
- A 3.9 µs history-induced gap shift is about half the 7.9–10.7 µs failure boundary, so history could decide a near tie that isn't in this 10-sample chain.

### 3.3 Phase 2: stress audit (Variant 3)
Source: [v3/phase2_audit.json](summary/v3/phase2_audit.json); per device: [v3/phase2_devices.csv](summary/v3/phase2_devices.csv).
- **Runs** (chosen from inputs): largest total input #17, smallest #61, largest column score #29, smallest column score #1, and the Variant 3 chain step #31 (started from chain step #30's end state).
- **Coverage:** every top-level node saved at full resolution over 0–3008 µs, reset included. All 134 TFTs audited, including the 21 crossbar instances. `rev10/sim/tools/audit.py` gives the same maxima (`raw/v3/phase2/*.audit.txt`).
- **Result: 0 devices above 3.5 V.**

| Rank | Device | Role | max \|V_G·\| (V) | Margin (V) | When |
|---|---|---|---|---|---|
| 1 | X80 | idle pull-down of `win` (6× L) | 3.339 | 0.161 | 10.6 µs (reset; `win` overshoots VDD) |
| 2–5 | XNP3, XNP5, X104, X124 | `na` precharge / latch load A | 3.308 | 0.192 | 10.7 µs (reset) |
| 6–8 | XNP1, XNP2, XNP4 | `na` precharge | 3.300 | 0.200 | 0 µs |
| 9 | XWR | `win` precharge | 3.300 | 0.200 | 20 µs |
| 10 | X69 | CREF reset | 3.300 | 0.200 | 151 µs |

- All 10 worst cases fall in the host reset phase.
- **Crossbar:** max 2.43 V (X19/X20/X23, at 301 µs, the row step into calibration). That's above the old ≈ 2.3 V analytic bound and 1.07 V below the limit.

### 3.4 Phase 3A: global corner window (Variant 3)
- **Setup.** The fixed 20-sample subset ([phase3_subset.json](summary/phase3_subset.json); 4 per class, including #31 and #81) was chosen before any Phase 1 result. Corners are one-dimensional sweeps (`rev10/sim/models/fitc10_sweep.lib`).
- **Host levels stay at the nominal `fitc10` values** (V₁ 1.82 V, V₂ 2.40 V); the host isn't re-trimmed per corner.
- **Warm start:** the nominal-corner Variant 3 warm start, for every point (an approximation).
- Source: [v3/phase3A.json](summary/v3/phase3A.json). C2 slopes: [v3/phase3A_c2slope.json](summary/v3/phase3A_c2slope.json).

| Point | Accuracy (Wilson 95 %) | Validity | Failures | Race from C2, median (max) | Lock latency, median | C2 rail slope (mV/µs) |
|---|---|---|---|---|---|---|
| \|V_th\| 0.45 V | 0/20 = 0 % (0–16) | 0/20 | stuck_latched ×20 | — | — | 1.90 |
| \|V_th\| 0.55 V | 14/20 = 70 % (48–85) | 19/20 | multi-latched ×1 | 424 (604) µs | 21.9 µs | 1.18 |
| **\|V_th\| 0.65 V (nominal = Phase 1 runs)** | **15/20 = 75 % (53–89)** | 20/20 | — | 879 (1148) µs | 19.3 µs | 0.63 |
| \|V_th\| 0.75 V | 13/20 = 65 % (43–82) | 18/20 | timeout ×2 | 1984 (2443) µs | 29.4 µs | 0.28 |
| \|V_th\| 0.85 V | 0/20 = 0 % (0–16) | 0/20 | timeout ×20 | — | — | 0.091 |
| \|V_th\| 0.95 V | 0/20 = 0 % (0–16) | 0/20 | timeout ×20 | — | — | 0.021 |
| \|V_th\| 1.05 V | 0/20 = 0 % (0–16) | 0/20 | timeout ×20 | — | — | 0.0035 |
| µ ×0.5 | 8/20 = 40 % (22–61) | 10/20 | timeout ×6, multi ×2, none ×2 | 2301 (2477) µs | 35.6 µs | 0.32 |
| µ ×0.75 | 14/20 = 70 % (48–85) | 19/20 | multi-latched ×1 | 1427 (1704) µs | 24.7 µs | 0.48 |
| µ ×1.25 | 15/20 = 75 % (53–89) | 20/20 | — | 534 (797) µs | 16.1 µs | 0.79 |

- **Working range** with fixed host levels: **|V_th| ≈ 0.55–0.75 V** (batch spread ±0.09 V around 0.65 V fits; end-of-life drift of +0.1 V is at the edge, +0.2 V or more fails) and **µ ×0.75–×1.25**.
- **|V_th| ≥ 0.85 V is a stall, not a window artefact.** The C2 overdrive is 3.3 − V₂ − |V_th|: 0.25 V at nominal, 0.05 V at 0.85 V, and below threshold beyond that. The rail slope collapses from 0.63 to 0.09 mV/µs and below. The protocol defines V₁ and V₂ relative to V_th, so this sweep mainly measures what happens when the host **doesn't** re-trim them. A tracked-level sweep wasn't run (§6).
- **|V_th| 0.45 V:** all five latches stay high from the `na` precharge, because the 6×-long latch-A loads can't pull them low at this V_th (`stuck_latched`).
- **µ ×0.5:** races of 2.0–2.5 ms run into the 2.5 ms window, and lock latency grows to 36 µs.

#### 3.4b Re-trimmed corner sweep (3A-T): process window with host trim
- **Setup (D12):** same 20 samples, corners and warm start. The host levels follow build_A's formula for the corner's |V_th|: V₁ = 3.3 − |V_th| − 0.83, V₂ = 3.3 − |V_th| − 0.25.
- **"Strict"** counts a race that trips during integration (before C2) as a failure, even when one class latches, because the result is then no longer decided by the scheme-A race.
- Source: [v3/phase3A_T.json](summary/v3/phase3A_T.json).

| \|V_th\| (V) | V₁ / V₂ (V) | **Fixed levels**: accuracy / validity | **Re-trimmed**: accuracy (Wilson 95 %) | Validity | Trips in C1 | **Strict** accuracy (Wilson 95 %) | Race from C2, median (range) | Lock, median | `ref` − reset (V) |
|---|---|---|---|---|---|---|---|---|---|
| 0.65 (nominal) | 1.82 / 2.40 | 75 % / 100 % | 75 % (53–89) | 20/20 | 0 | 75 % | 879 µs | 19.3 µs | 0.477 |
| 0.75 | 1.72 / 2.30 | 65 % / 90 % | **75 %** (53–89) | 20/20 | 0 | 75 % (53–89) | 681 µs (294–952) | 18.5 µs | 0.441 |
| 0.85 | 1.62 / 2.20 | 0 % / 0 % | **70 %** (48–85) | 19/20 | 0 | 70 % (48–85) | 477 µs (87–750) | 19.5 µs | 0.404 |
| 0.95 | 1.52 / 2.10 | 0 % / 0 % | **65 %** (43–82) | 18/20 | 2 | **60 %** (39–78) | 271 µs (−6–548) | 21.2 µs | 0.365 |
| 1.05 | 1.42 / 2.00 | 0 % / 0 % | **55 %** (34–74) | 15/20 | 9 | **35 %** (18–57) | 59 µs (−27–346) | 23.1 µs | 0.323 |

- **Two readings:**
  - **Drift budget, no re-trim** (fixed levels, §3.4): |V_th| may drift from 0.65 to about 0.75 V before the C2 overdrive collapses.
  - **Process window, with re-trim:** the design classifies at 65–75 % up to 0.95 V, and degrades at 1.05 V.
- **What limits re-trimmed operation:**
  - **The voltage window shrinks.** `ref` − rail reset level goes from 0.48 V at 0.65 V to 0.32 V at 1.05 V. This is the lab-corner "window ≈ V_DD − 2|V_th|" rule.
  - **Strong samples trip during integration.** As the window shrinks they reach the trip level before C2: 2/20 runs at 0.95 V and 9/20 at 1.05 V. This is the start of the failure seen at 1.15 V at the lab corner ([docs/TOOLING.md](../../docs/TOOLING.md) §3).
  - **Near-tie double latches rise:** 1, 2 and 5 at 0.85, 0.95 and 1.05 V.

### 3.5 Phase 3B: local-mismatch Monte Carlo (Variant 3). ALL SPREADS ASSUMED.
- **Assumed spreads:**
  - σ_Vth ∈ {20, 40, 80} mV, the **same for every device geometry**. No Pelgrom area scaling, so large devices (comparator sense 468×15 µm, rail reset 400×20 µm) get the same σ as 10×5 µm devices. The campaign specification treats 80 mV as an upper bound (batch spread).
  - σ_µ/µ 10 %, normal.
  - R_C lognormal, σ 20 %.
- **Draws:** independent per device, on all 134 TFTs including the 21 crossbar instances (one draw per instance, i.e. per finger bank). They're applied through the new `*_mc.sub` model copies; a zero-spread die reproduces the nominal run exactly ([mc_equiv.json](summary/mc_equiv.json)).
- **Size:** 5 dies per level (D8), the same 20 samples, die seed = 1000·σ_mV + die.
- Source: [v3/phase3B.json](summary/v3/phase3B.json); draws per run: `raw/v3/phase3B/*_draws.json`.

| σ_Vth (assumed) | Dies | Accuracy: median die / worst / best | Pooled accuracy (Wilson 95 %) | Validity: median die / worst | Pooled failures | Dominant-class share, median die |
|---|---|---|---|---|---|---|
| 0 (nominal, Phase 1 runs) | 1 | 75 % | 15/20 (53–89 %) | 100 % | — | — |
| 20 mV | 5 | **40 %** / 25 % / 50 % | 39/100 (30–49 %) | 95 % / 90 % | multi-latched ×5 | 61 % |
| 40 mV | 5 | **40 %** / 30 % / 50 % | 41/100 (32–51 %) | 100 % / 95 % | multi-latched ×1 | 60 % |
| 80 mV | 5 | **30 %** / 20 % / 45 % | 31/100 (23–41 %) | 100 % / 95 % | multi-latched ×2 | 90 % |

- **Reading.** Under this mismatch model, accuracy falls from 75 % to 30–40 % (chance is 20 %), while validity stays ≥ 90 %. The circuit still produces exactly one winner, but mismatch reorders classes.
- **Each die is biased.** The median die sends 60–90 % of its valid predictions to one class; at 80 mV, die 1 sends 100 % to class 5. That points to fixed per-class offsets rather than random per-sample noise.
- **Plausible sources (not isolated by these runs):**
  - the rail reset level, which follows the reset switch's V_th one-for-one;
  - the comparator sense device's offset;
  - the per-bank crossbar currents.
- **Offsets vs gaps.** Two classes' offsets combine to ≈ 40 mV at σ_Vth 20 mV (my estimate, two devices per class). That is comparable to the nominal runner-up gap in volts: median 67 mV, 5th percentile 18 mV ([v3/phase1.json](summary/v3/phase1.json), `runner_up_gap_mV`).
- With 5 dies per level the die-to-die spread (20–50 %) is as large as the trend between 20 and 40 mV. The flat-σ results are kept as a **worst-case bound** for the large devices: the comparator and reset switches get the full σ.

#### 3.5b Size-scaled mismatch: 3B-V (V_th only) and 3B-P (unphysical bound). ALL SPREADS ASSUMED.
- **3B-V, the size-scaled estimate (D13):** σ_Vth = anchor·√(780 µm²/(W·L)) per instance (build_final.py convention), anchors **20 and 35 mV**, **µ and R_C nominal**.
- **3B-P, an unphysical upper bound (D12):** the same V_th scaling with anchors 20, 35 and 50 mV, but the µ (10 %) and R_C (20 %) spreads were **also** scaled by √(780/WL). **That µ/R_C scaling was the author's mistake** (D13): those spreads should have stayed flat per device. It gave the 10×5 µm logic devices σ_µ ≈ 39 % and σ_RC ≈ 79 % at every anchor. 3B-P is kept only as an unphysical upper bound on mismatch damage.
- **Pairing:** all three models use the same 20 samples and 5 dies per level, with seed = 1000·anchor + die.
  - 3B-V and 3B-P dies have **identical V_th draws**, because the µ/R_C numbers are drawn in 3B-V but not applied.
  - The anchor-20 dies also share their random numbers with the flat 20 mV dies.
- Sources: [v3/phase3B_V.json](summary/v3/phase3B_V.json) (including `pairs`), [v3/phase3B_P.json](summary/v3/phase3B_P.json), [v3/phase3B.json](summary/v3/phase3B.json). Failure labels from `summarize.py::failure` (the same for all three).

| Model | Level | Pooled accuracy (Wilson 95 %) | Pooled validity | Accuracy: median die / worst / best | Failures (pooled, 100 runs per level) | Dominant-class share, median die |
|---|---|---|---|---|---|---|
| No mismatch (Phase 1 runs) | — | 15/20 = 75 % (53–89) | 20/20 | — | — | — |
| **Size-scaled V_th only (3B-V)** | anchor 20 mV | **64/100** (54–73 %) | 95/100 | 65 / 55 / 70 % | near-tie multi-latched 5 | 32 % |
| **Size-scaled V_th only (3B-V)** | anchor 35 mV | **57/100** (47–66 %) | 94/100 | 60 / 45 / 65 % | near-tie multi-latched 6 | 35 % |
| Flat σ, worst-case bound (§3.5) | 20 / 40 / 80 mV | 39 / 41 / 31 of 100 | 95 / 99 / 98 | median 40 / 40 / 30 % | near-tie multi-latched 5 / 1 / 2 | 61 / 60 / 90 % |
| Size-scaled V_th **and µ/R_C** (3B-P, unphysical) | anchor 20 / 35 / 50 mV | 17 / 4 / 21 of 100 | 26 / 6 / 37 | median 5 / 0 / 20 % | lockout_failed 51 / 33 / 59; stuck_latched 20 / 40 / 0; timeout 0 / 20 / 0; near tie 3 / 1 / 4 | — |

- **Paired comparisons** (`pairs` in [v3/phase3B_V.json](summary/v3/phase3B_V.json)):
  - **3B-V vs 3B-P, same V_th draws** (200 die-sample pairs): 121 vs 21 correct, 189 vs 32 valid, the same outcome in 41. Removing the µ/R_C scaling removes the logic failures. So in 3B-P the lockout and stuck-latch failures came from the µ/R_C spreads on the small logic devices, not from their V_th spread.
  - **3B-V anchor 20 vs flat 20 mV, same random numbers** (100 pairs): 64 vs 39 correct, both 95 valid, the same outcome in 50. Scaling σ down on the large devices (comparator sense ×0.33, rail reset switch ×0.31, crossbar banks ×0.19–0.85) removes most of the per-class bias. The median die's dominant-class share falls from 61 % to 32 %.
- **Reading.**
  - Under the size-scaled V_th model, accuracy drops from 75 % to 64 % (anchor 20 mV) and 57 % (anchor 35 mV), with validity ≥ 94 %.
  - All failures are near-tie double latches. There's no lockout failure, stuck latch or timeout in 200 runs.
  - With 5 dies per level the die-to-die range (45–70 %) is wider than the step between anchors.
- **Device list (D13 item 2) not triggered.** 3B-V has no lockout or stuck-latch failures, so there are no failing dies or classes to correlate. The correlation script `scripts/failure_devices.py` is committed. Its output for the unphysical 3B-P is in [v3/failure_devices_phase3B_P.json](summary/v3/failure_devices_phase3B_P.json) for reference only.

### 3.6 Variant 1: CREF sensitivity (measured)
Variant 1 is Variant 3 with CREF at 24 pF instead of 140.88 pF; everything else is identical. It was run through Gate B, the full Phase 1 (90 + chain), Phase 2, and part of Phase 3 (stopped on author instruction when Variant 3 was adopted). It measures what CREF does to the design.

**Phase 1 and Phase 2 comparison.** Source: [v1_vs_v3.json](summary/v1_vs_v3.json), built from [phase1.json](summary/phase1.json), [v3/phase1.json](summary/v3/phase1.json), [phase2_audit.json](summary/phase2_audit.json) and [v3/phase2_audit.json](summary/v3/phase2_audit.json).

| | Variant 1 (CREF 24 pF) | Variant 3 (CREF 140.88 pF) |
|---|---|---|
| `ref` at end of sampling (311 µs) | 2.42 V | 1.38 V |
| Race time from C2, median (range) | 1300 µs (923–1583) | 870 µs (493–1148) |
| Accuracy | 62/90 = 68.9 % (58.7–77.5) | 62/90 = 68.9 % (58.7–77.5) |
| Validity | 87/90 | 87/90 |
| Failures | multi-latched ×3 (#24, #25, #42) | same 3 samples |
| Per-sample outcome | 90/90 identical | 90/90 identical |
| Runner-up gap, median / min | 103.0 / 10.74 µs | 102.1 / 10.75 µs (largest per-sample difference 1.06 µs, ≤ 2.6 %) |
| Lock latency, median (range) | 17.0 µs (16.8–18.8) | 19.2 µs (19.1–20.0) |
| Gap − latency, min / 5th percentile | −6.7 / 9.7 µs | −8.9 / 7.8 µs |
| Valid runs with gap < latency | 3 | 4 |
| Chain: same outcome / max trip shift | 10/10 / 4.3 µs | 10/10 / 4.1 µs |
| Stress: devices > 3.5 V | 0/134 | 0/134 |
| Worst device | X80, 3.339 V | X80, 3.339 V |
| Crossbar max | 2.429 V | 2.429 V |
| Largest per-device stress change | — | X66 (`ref` follower): 2.48 → 1.95 V |

**Reading.**
- CREF ×5.87 lowers `ref` by ≈ 1 V and shortens the race about 1.5× (median), but it **doesn't change any classification**. All rails rise at the same rate in C2, so the time gap between them is set by their spacing at the end of C1, independent of the trip threshold.
- What CREF does change: the lock latency, ≈ 2.2 µs longer at the lower `ref`, which slightly reduces the near-tie margin. And X66's gate stress, 0.5 V lower.
- **Variant 1 Phase 3 (partial: 3A only; 20 samples per point except 0.95 V).** Source: [phase3A.json](summary/phase3A.json).

  | \|V_th\| (V) | N | Accuracy | Validity | Failure | Race from C2 (median) |
  |---|---|---|---|---|---|
  | 0.45 | 20 | 0 % | 0 % | stuck_latched ×20 (latches never reset low) | — |
  | 0.55 | 20 | 75 % | 100 % | — | 706 µs |
  | 0.65 (= Phase 1 runs) | 20 | 75 % | 100 % | — | 1311 µs |
  | 0.75 | 20 | 10 % | 10 % | timeout ×18 (race ≈ 2.3 ms, beyond the 2.5 ms window) | 2305 µs |
  | 0.85 | 20 | 0 % | 0 % | timeout ×20 | — |
  | 0.95 | 12 | 0 % | 0 % | timeout ×12 | — |

  The µ sweep and Phase 3B were not run for Variant 1.

  **Shared |V_th| points, Variant 1 vs Variant 3** ([v1_vs_v3.json](summary/v1_vs_v3.json), `phase3A_shared_points`):

  | \|V_th\| (V) | V1 accuracy / validity | V3 accuracy / validity | Race median V1 / V3 |
  |---|---|---|---|
  | 0.45 | 0 % / 0 % (stuck) | 0 % / 0 % (stuck) | — |
  | 0.55 | 75 % / 100 % | 70 % / 95 % | 706 / 424 µs |
  | 0.65 | 75 % / 100 % | 75 % / 100 % | 1311 / 879 µs |
  | 0.75 | **10 % / 10 %** (timeout ×18) | **65 % / 90 %** | 2305 / 1984 µs |
  | 0.85 | 0 % (timeout) | 0 % (timeout) | — |
  | 0.95 | 0 % (timeout; 12 samples) | 0 % (timeout) | — |

  The larger CREF shortens every race, which moves the |V_th| = 0.75 V point back inside the 2.5 ms window. It doesn't help at ≥ 0.85 V, where the C2 slope itself collapses.

## 4. What this does not show
- **Not real data.** The dataset is synthetic (`clinical_validation: false`).
- **Wrong substrate.** `fitc10` comes from C10-DNTT on **Si** (Kraft 2016), with currents read by eye (±0.3 µA), applied to a flexible-foil design. JOFF and LOV aren't fitted.
- **Rebuilt sizing.** The `fitc10` sizing (Variant 3) is rebuilt from the author's decisions, one of them (D11) made after seeing the data. It matches the gate samples; it isn't a confirmed copy of the lost design.
- **Assumed mismatch.** Both mismatch models are assumptions with 5 dies per level:
  - **Flat σ** (30–40 %) is a worst case for the large devices.
  - **Size-scaled V_th only** (57–64 %) is the closest to the base-design convention, but its anchors (20–35 mV at 780 µm²) are a bracket, not a measurement.
  - **3B-P** (4–21 %) is an unphysical bound: it scaled µ/R_C with area by mistake.
  - Neither is calibrated to measured C10-DNTT mismatch, which doesn't exist.
  - Phases 1–2 are nominal dies only.
- **No ageing data.** There's no C10-DNTT bias-stress data; the V_th sweep is only a proxy for drift. The fixed-level sweep shows the budget without re-trim; 3A-T shows the window with re-trim. It doesn't show how accurately a real host could measure |V_th| to re-trim.
- **Weights not trained for scheme A.** SPICE accuracy (68.9 %) sits next to the weights' software ceiling (70.0 %). Accuracy is limited by the weights, not the circuit, at this corner.
- **Absolute timing is unreliable** (10–17 % in earlier work). Read only ordering and gaps.
- **No layout parasitics, IR drop or noise.** Noise could flip near ties: 7 of 90 samples have runner-up gaps under 20 µs ([v3/phase1_runs.csv](summary/v3/phase1_runs.csv), `gap_reach_us`).
- **One prior history.** All independent runs start from one end state (class 5 won); only 10 samples were chained.
- **N = 90:** the accuracy CI is ≈ ±10 points.

## 5. Anomalies and open questions
- **`ref` is a timed charge, not a settled sample,** in every variant and at the lab corner. Its final level depends on CREF, on the current through the dummy column, and on the 8 µs calibration window. So race time depends on mobility, V_th and timing as well as the inputs; Phase 3A measures that.
- **Near-tie failures** come from slow latch regeneration (≈ 25 µs from 1.4 to 3.1 V on `na`). A second rail within ≈ 8 µs also latches. Lock latency (17–20 µs) isn't the binding limit: valid runs exist with gaps of 10.7 µs, below the latency.
- **Crossbar stress exceeds the old analytic bound** (2.43 vs 2.3 V), at the row step into calibration. Still within the limit.
- **|V_th| = 0.45 V, both variants:** all latches stay high from the `na` precharge, because the 6×-long latch-A loads can't pull them down. The low-V_th side of the window is set by the load resize (D4), not by the race.
- **Tooling:**
  - Two workers creating the same symlink at once crashed one Variant 3 Gate B run; it was fixed and repeated with identical results.
  - Two wait loops matched their own command lines; they were fixed.
  - None of this affected any result.

## 6. Proposed changes and follow-ups (not in the main results; none were run unless marked done)
1. **Done (3A-T):** tracked host levels; see §3.4b.
2. **Done (3B-P):** size-scaled mismatch with µ/R_C also scaled. By the author's account (D13) that µ/R_C scaling was a mistake, so it's kept only as an unphysical upper bound; see §3.5b.
3. **Done (3B-V):** V_th-only size-scaled mismatch; see §3.5b. It separates the 3B-P failure cause: the µ/R_C spreads on the small logic devices, not their V_th.
4. **Ratioed-logic robustness.** Not supported by the physical models: 3B-V and flat σ produce no lockout or stuck-latch failures. It would only matter if real C10-DNTT mobility/contact mismatch on 10–20 × 5 µm devices were as large as the unphysical 3B-P assumption (σ_µ ≈ 40 %). No device list is given (D13 item 2 not triggered). Not simulated.
5. **Per-class offset reduction** (circuit; relevant to the flat-σ bound). Candidates:
   - reset rails to a host-driven level instead of the reset switch's V_th floor;
   - auto-zero the comparator;
   - widen the C1 voltage gap between classes.
   Evidence: §3.5 class bias under flat σ; ≈ 40 mV estimated offsets against a 67 mV median gap. Under size-scaled V_th (§3.5b) the bias mostly disappears, and the loss (75 → 57–64 %) comes from near ties. Not simulated.
6. **High-V_th window** (protocol or circuit). With re-trim, the limit at ≥ 0.95 V is trips during integration as `ref` − reset shrinks (§3.4b). A shorter T₁ or a lower V₁ at high |V_th| would be the protocol-side lever. Not simulated.
7. **Latch regeneration speed** (circuit). The nominal failures are near ties within ≈ 8 µs, and `na` takes ≈ 25 µs to regenerate (§3.2). Not simulated.
8. **Variant 3's CREF** is the adopted design (D11). The sensitivity in §3.6 shows CREF sets race time and the usable fixed-level |V_th| range, but not nominal accuracy.
