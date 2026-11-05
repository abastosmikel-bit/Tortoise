# fitc10 rebuild: decisions (recorded 2026-10-22, before any fitc10 simulation)

The original `fitc10` corner card and resized netlist were lost and won't be recovered. The rebuild below rests on **decisions by the author** (who ran the original `fitc10` work), based on their reading of their own notes. These are **decisions, not recovered facts**. A Gate B match is a **check of the rebuilt sizing**, not a reproduction of the lost runs.

## D1. Corner: `rev10/sim/models/fitc10.lib`, section `fitc10` (new file)
`MU=5.87 CI=0.70e-6 SS=0.112 RCW=490 JOFF=1e-14 VTH0=0.65 LOV=2`
- MU, VTH0, SS, RCW: from the campaign specification (Kraft 2016, C10-DNTT on **Si**; saturation currents read by eye, ±0.3 µA).
- CI: lab value.
- **JOFF and LOV: kept at the lab values. Not fitted (assumption).**

## D2. Base netlist: `rev10/sim/circuits/t5L_x2_v065.cir`
Byte copy of `t5L_x2_v085.cir` with only the `.lib` line changed, to `.lib ../models/fitc10.lib fitc10`. Built with `VTH=065` (`build_A.build(..., vth="065")`). Row levels follow the V_th-referenced formula: **V₁ = 1.82 V, V₂ = 2.40 V**.

## D3. Capacitors
Only `CRAIL1–5` scale ×5.87: 375 pF → **2201.25 pF**. `CREF` stays at 24 pF (it holds a sampled reference and doesn't integrate rail current). All other capacitors are unchanged.

## D4. Loads: Variant 1 (primary)
Every TFT with **drain = 0 and gate = 0** in the final build (after `build_A`/`lockvar`/variant C) gets **L ×6, W unchanged**. Devices with gate = 0 and source = `vdd` don't count. Applied by `scripts/common.py::build`. Devices changed (19):

| Device | Source node | W (µm) | L before → after (µm) |
|---|---|---|---|
| X62 (self-biased pull-down) | n1 | 20 | 10 → 60 |
| X64 (tracking load) | comp | 33 | 10 → 60 |
| X80 (idle pull-down of win) | win | 5 | 20 → 120 |
| XI2 (inverter load) | lockb | 10 | 5 → 30 |
| X82, X92, X102, X112, X122 (detect loads) | d1–d5 | 20 | 20 → 120 |
| X84, X94, X104, X114, X124 (latch load A) | na1–na5 | 10 | 20 → 120 |
| X87, X97, X107, X117, X127 (latch load B) | nb1–nb5 | 20 | 5 → 30 |

- **X136** (named in the decision) isn't present in the final build. `t10.py` comments it out together with the rest of SEQ8 ("removed (SEQ8 replaced by host timing)"), so there's nothing to change.
- X134 and X138 (gate 0, source vdd) are also commented out by `t10.py`.

## D5. Loads: Variant 2 (fallback, run **only** if Variant 1 fails Gate B)
Same as Variant 1, but the 6× applies only to the logic-chain loads: the X82/X84/X87 families, XI2 and X80 (17 devices). X62 and X64 keep their original sizes. No other variants.

## D6. Gate B (fixed before running)
Both runs use the borrowed prior `t6L_x2_v085` (a lab-corner end state, class 5 won), `RELAX=1` solver settings, and a race window of 1200 µs after the start of C2 (`.tran` to 1708 µs).

| Run | Pass criteria (all required) |
|---|---|
| #81 (`X_test[81]`, label class 5) | valid (exactly one class latched, and it's the first tripper), latched = 5, no trip before C2 starts, **lock latency 15–25 µs** |
| #31 (`X_test[31]`, label class 2) | valid, latched = 2 |

- "Lock latency" uses the `score.py` definition: the time `win` crosses 2.05 V minus the time the winner's `na` crosses 1.65 V. The `lockb` chain time (`lockmeas.py` definition) is reported as a secondary measure.
- The 15–25 µs band is my reading of "≈ 20 µs", fixed now.
- Sequence: Variant 1 → if it fails either run, Variant 2 → if that also fails, **stop and report**.

## D7. Warm start
After Gate B, `fitc10` end states are chained: repeated #81 runs, each starting from the previous run's end state, beginning from the borrowed prior. The chain stops when every rail reset level (`ap1–5` at 311 µs, just before `rstr` releases) changes by **< 5 mV** between consecutive runs. The last end state becomes the Phase 1–3 warm start. #81 is used because its end state matches the borrowed prior's history (class 5 won).

## D8. Phase 3B
Cut to 5 dies per σ level (author decision).

## D6 outcome and amendment (recorded 2026-10-22, after Gate B; disclosed post-hoc change)
- **Gate B as fixed above (1200 µs window): FAILED for both variants.** Source: `summary/gateB_v1.json`, `summary/gateB_v2.json`.
  - Variant 1: #81's class 5 tripped at 1706.8 µs, 0.7 µs before the window ended, so nothing latched yet. #31 had no trip.
  - Variant 2: both runs timed out.
  - Every failure is "race not finished". None is a wrong class.
- **Diagnosis:** `ref` is set by a timed charge of CREF (24 pF) from the dummy columns `acol1–5` during calibration (302–310 µs). It's still ramping when sampling ends. At `fitc10` it reaches 2.41 V, against 1.76 V at the lab corner, because the dummy-column current scales with µ while CREF doesn't. So the trip level sits about 0.6 V higher, and at the common C2 slope (≈ 0.63 mV/µs) the race takes ≈ 1200 µs.
- **Diagnostic, simulation setting only:** Variant 1 with a race window of **2500 µs** after C2 meets every Gate B criterion. Source: `summary/diag_window_v1.json`. #81's trip time is identical to the 1200 µs run (1706.833 µs), so the window didn't change behaviour.
- **Amendment:** Phases 0.3–3 use **Variant 1 with a 2500 µs window after C2 starts** (`.tran` to 3008 µs).
  - The 1200 µs value was my choice; the campaign specification asks for "at least 1.2 ms".
  - The Gate B criteria are unchanged. Variant 2 isn't used further.
- **Open discrepancy:** the race takes ≈ 1200–1250 µs, against the campaign specification's "≈ 800 µs" for the lost runs. A plausible cause is that the lost design also scaled CREF, but that would be a circuit change. It isn't run here; see REPORT §6.

## D9. Variant 3 (author decision, 2026-10-22, recorded before running it)
- **Variant 3 = Variant 1 + CREF ×5.87:** 24 pF → **140.88 pF** ("141 pF").
- It's a **proposed correction to D3**, not tuning. Physical reason: `ref` is set by integrating the calibration (dummy-column) current on CREF, so CREF should scale with that current, just as CRAIL scales with the integration current.
- Runs: #81 and #31, borrowed prior `t6L_x2_v085`, 2500 µs window. Script: `scripts/gateB_v3.py`.
- Criteria, all required on both runs:
  1. the Gate B criteria of D6;
  2. **race time < 1200 µs** (first trip − C2 start);
  3. **`ref` settled at the end of sampling:** `ref` changes by **< 5 mV between 308 and 309 µs**. The sampler X67 is on until `phib` rises at 309–310 µs. Variant 1 changes by 171 mV over that interval, and the lab corner by 131 mV.
- **If Variant 3 meets 1–3:** Phase 1 is rerun on Variant 3 and Phase 3 runs on Variant 3, with a new Variant 3 warm start built by the D7 procedure. I'll also rerun the chain and the Phase 2 audit on Variant 3 (my addition: CREF changes the `ref` reset, which is the known history-dependent node).
- **Otherwise:** Phase 3 runs on Variant 1, and every Phase 3 result carries the `ref`-settling caveat.

## D10. Status of Variant 1 (author instruction, 2026-10-22)
Gate B passed on **class, validity and lock latency only**. The race takes ≈ 2× the original ≈ 800 µs, and `ref` hasn't settled at the end of sampling (it ends ≈ 0.6 V above the lab corner). Variant 1 is a **rebuilt design that classifies correctly, not a confirmed copy of the original**. All Phase 1 results are labelled "Variant 1".

## D11. Variant 3 adopted as the main design (author decision, 2026-10-22, made AFTER seeing the Variant 1 and Variant 3 Gate B data)
- **The D9 criterion "`ref` settled (< 5 mV over 308–309 µs)" is withdrawn by the author as wrong.** The lab-corner reference design doesn't settle either (131 mV over the same interval). `ref` is a timed charge by design.
- **It's replaced by: race time consistent with the original ≈ 800 µs.**
  - Variant 3 meets it: #81 773 µs, #31 831 µs (`summary/gateB_v3.json`).
  - Variant 1 doesn't: 1199 / 1254 µs (`summary/diag_window_v1.json`).
- **Variant 3 (Variant 1 + CREF 24 → 140.88 pF) is adopted as the main design.** This decision was made after the data was seen. It's recorded here as such, not as a pre-registered outcome.
- **Variant 1's role:** a measured sensitivity result (effect of CREF ×5.87), reported in its own section. Its Phase 3 run was stopped on author instruction and is kept as partial: 3A complete for |V_th| 0.45/0.55/0.75/0.85 V, 12/20 at 0.95 V; µ points and 3B not run.
- **Plan for Variant 3:** same scripts, settings, 2500 µs window, Phase 3 subset and seeds as Variant 1. Outputs go to `raw/v3/` and `summary/v3/` (`FC10_VARIANT=3`).
  - 0e: own warm start (D7 procedure, from the borrowed prior);
  - Phase 1: 90 samples + chain 30–39;
  - Phase 2: the same 5 audit runs (chain run from the Variant 3 chain);
  - Phase 3: 3A and 3B at 5 dies per σ.

## D12. Follow-ups on Variant 3 (author request, 2026-10-25, after the main Phase 3; recorded before running)
- **3A-T, re-trimmed corner sweep.** |V_th| 0.75 / 0.85 / 0.95 / 1.05 V (corners `fc10_vthXXX`), with the host row levels re-trimmed by build_A's own formula: V₁ = 3.3 − |V_th| − 0.83 (calibration and C1) and V₂ = 3.3 − |V_th| − 0.25 (C2). Same 20 samples, same warm start, same 2500 µs window. Outputs: `raw/v3/phase3A_T/`, `summary/v3/phase3A_T.json`.
  - Reporting: next to the fixed-level sweep. Fixed levels = drift budget without re-trim; re-trimmed = process window with re-trim.
- **3B-P, size-scaled mismatch.** σ = anchor·√(780 µm²/(W·L)) per instance (build_final.py convention), with V_th anchors **20, 35 and 50 mV** (the lab-corner 20–50 mV bracket). The same factor applies to the µ draw (10 % at 780 µm²) and the R_C draw (lognormal 20 % at 780 µm²).
  - Crossbar banks use their instance W·L (10 µm × fingers × 54 µm).
  - The resulting factor runs from 0.19 (largest devices) to 3.95 (10×5 µm devices). At the 50 mV anchor the smallest devices get σ_Vth ≈ 200 mV, σ_µ ≈ 39 % and σ_RC ≈ 79 %. The KMU clip at 0.2 is kept.
  - 5 dies × 20 samples per anchor. Seed = 1000·anchor + die, so the anchor-20 dies use the same underlying random numbers as the flat 20 mV dies (paired).
  - Outputs: `raw/v3/phase3B_P/`, `summary/v3/phase3B_P.json`. The flat-σ results stay in the report as a worst-case bound.
- **Checks before running:**
  - a flat-σ die rebuilds byte-identical to its saved netlist;
  - the re-trimmed levels at 0.85 V come out at V₁ 1.62 V / V₂ 2.20 V;
  - the size-scaled draws equal the flat draws × √(780/WL) per device (ratio 0.99998–1.00001).
- **Waveform storage:** `*.csv.gz` waveforms, `*.cir.gz` netlists and `*_draws.json` move to Git LFS, and the branch history is rewritten so main never receives the blobs. Per-run metric JSONs, summaries and scripts stay in git. *(Public release: these files are not included; they can be regenerated by re-running the campaign, see [REPRODUCE.md](../../REPRODUCE.md) §6.)*

## D13. V_th-only size-scaled mismatch (author decision, 2026-10-25, after seeing 3B-P; recorded before running)
- **The author states that scaling the µ and R_C draws with √(780/WL) in 3B-P was a mistake** (author's instruction in D12): those spreads should have stayed flat per device. **3B-P is kept in the report as an unphysical upper bound**, not as a mismatch estimate.
- **3B-V:** σ_Vth = anchor·√(780 µm²/(W·L)) per instance, anchors **20 and 35 mV**, **µ and R_C nominal** (KMU = KRC = 1). The same seeds, dies and samples as 3B-P.
  - The µ/R_C random numbers are still drawn but not applied, so every die's V_th draws are identical to its 3B-P counterpart (checked: identical to 1e-12 for anchor-20 die 1).
  - Outputs: `raw/v3/phase3B_V/`, `summary/v3/phase3B_V.json`. Reported next to flat σ and 3B-P with the same failure labels.
- **If 3B-V still shows `lockout_failed` or `stuck_latched` failures:** list the devices whose draws correlate with the failing dies or classes, in the proposals section. Don't resize anything.
- **Correction to D12 "Waveform storage":** the history was **not** rewritten; the files were moved to LFS in a normal commit (storage only, no result affected).
