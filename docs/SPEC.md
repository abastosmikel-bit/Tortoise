# Tortoise v1.0: specification

**Status: simulation-only design.** Nothing here has been fabricated or measured. Every number comes from ngspice-42
simulations of a compact OTFT model whose device corner is a reconstruction from a published Si-substrate dataset,
on a synthetic dataset. Each number links to the summary file it comes from; the same numbers are indexed in
[`RESULTS_INDEX.md`](../RESULTS_INDEX.md). Limits are listed in §6 and in each campaign report's "what this does not
show" section.

Tortoise v1.0 is not a new design. It names one consistent combination of things that already exist in this repository:

| Part | Tortoise v1.0 choice | Defined in |
|---|---|---|
| Device corner | `fitc10` (C10-DNTT, reconstructed) | [`rev10/sim/models/fitc10.lib`](../rev10/sim/models/fitc10.lib); [fitc10 DECISIONS D1](../results/fitc10_campaign/DECISIONS.md) |
| Circuit | frozen base-design build + **Variant 3** resize, 134 TFTs | [`docs/TOOLING.md`](TOOLING.md) §2; [fitc10 DECISIONS D3, D4, D9, D11](../results/fitc10_campaign/DECISIONS.md) |
| Weights | `rev10/eval/F_hw_m4_firstpass.npy` ("old weights") | [`docs/TOOLING.md`](TOOLING.md) §2; [weights_schemeA REPORT §9.5](../results/weights_schemeA/REPORT.md) |
| Host protocol | **v2.1** = v2 (H2 + H4) + adaptive power gating (P2) | [host_v2 DECISIONS H2, H4](../results/host_v2/DECISIONS.md); [host_v21 DECISIONS P2](../results/host_v21/DECISIONS.md) |
| Canonical netlist | [`docs/rev10_1_nominal.cir`](rev10_1_nominal.cir) (nominal die, test sample #81) | §2.4 below |

Contents: 1 device corner · 2 circuit · 3 weights · 4 host protocol v2.1 · 5 operating envelope · 6 failure modes and
limits · 7 file map.

---

## 1. Device corner: `fitc10`

All TFTs are p-type DNTT-family OTFTs on an AlOx/SAM gate dielectric, single 3.3 V rail, 3.5 V dielectric stress
limit ([`docs/TOOLING.md`](TOOLING.md) §2).

| Parameter (`.param` in `fitc10.lib`) | Value | Provenance |
|---|---|---|
| `MU` (band mobility) | 5.87 cm²/Vs | Kraft 2016, C10-DNTT **on Si**; saturation currents read by eye (±0.3 µA) |
| `VTH0` (\|V_th\|) | 0.65 V | same |
| `SS` (subthreshold swing) | 112 mV/dec | same |
| `RCW` (contact resistance × width) | 490 Ω·cm | same |
| `CI` (gate capacitance) | 0.70 µF/cm² | lab value (AlOx/SAM), author's decision |
| `JOFF` (off-current density) | 1e-14 A/µm | **assumption**: kept at the lab value, not fitted |
| `LOV` (gate overlap) | 2 µm | **assumption**: kept at the lab value, not fitted |

Source: [`rev10/sim/models/fitc10.lib`](../rev10/sim/models/fitc10.lib) header and
[fitc10 DECISIONS D1](../results/fitc10_campaign/DECISIONS.md). The original fitted `fitc10` card was lost; this card
is a **reconstruction from the values in the campaign specification** (fitc10 REPORT §2 and §4).

Model files (all in [`rev10/sim/models/`](../rev10/sim/models/)):
- `trace2_otft_v2.sub`: charge-based compact model (subthreshold, contact resistance, bias-dependent capacitance), used
  for every non-crossbar TFT.
- `trace2_otft_seg.sub`: 5-segment channel version (captures channel transit delay), used for the 21 crossbar banks.
- `trace2_otft_v2_mc.sub`, `trace2_otft_seg_mc.sub`: identical equations with per-instance `DVTH`, `KMU`, `KRC`
  multipliers for Monte Carlo; a zero-spread die reproduces the nominal run exactly
  ([fitc10 summary/mc_equiv.json](../results/fitc10_campaign/summary/mc_equiv.json)).
- `fitc10_sweep.lib`: one-dimensional corners `fc10_vthXXX` (\|V_th\| 0.45–1.05 V) and `fc10_muXXX` (µ ×0.5–×1.25).
  Later campaigns write further global corners as `eh_v<vth>_m<mu>.lib` with the same parameter values
  (`results/*/models/`).
- Mismatch convention used for the size-scaled estimates: σ_Vth = anchor·√(780 µm²/(W·L)) per instance, anchors
  20–35 mV; there is no published Pelgrom coefficient for this stack, so the anchors are a bracket
  ([fitc10 REPORT §3.5b](../results/fitc10_campaign/REPORT.md), [`docs/TOOLING.md`](TOOLING.md) §3).

---

## 2. Circuit

### 2.1 Base: the frozen base design (lab corner)
6-input × 5-class linear classifier. Each class integrates its weighted input current onto a rail capacitor; in
the race phase all rails ramp together and the first rail to reach the comparator threshold latches and locks out
the others ("integrate, then race", scheme A). Frozen elements, from [`docs/TOOLING.md`](TOOLING.md) §2:
- **Crossbar:** bank (i, k) is one `potftseg` instance, W = 10 µm × F[i, k] fingers, L = 54 µm; 60 fingers per
  column; empty banks are removed. Plus a 6 × 5 dummy ("inhibitory") column set (X31–X60, 38/10 µm) used only to
  charge `ref` during calibration.
- **Reset switches** X75–X79: 400/20 µm (sized for mismatch: each rail's reset level equals its switch's |V_th|).
- **Comparator (variant C), per class:** sense M81 468/15, detect load M82 20/20, trip driver M83 200/10 µm.
- **Lock (V2):** P_k 80/5, C_win 0.3 pF, `nb` load family 20/5, lock devices M89 20/5 gated by `lockb`, `win`
  precharge XWR from `rstr`; latch reset pulls `nb` up (M88 → `nb rstr vdd`).
- **Latch-history equaliser:** XNP1–5 (`na rstb vdd`, 20/5).
- **No negative supply**; gate-grounded loads; the on-chip sequencer (SEQ8) is removed and the host drives the
  timing lines. Note that power gating under v2.1 mode G drives internal nodes below 0 V (§6).

### 2.2 Variant 3: what differs from the base-design netlist
Applied by [`results/fitc10_campaign/scripts/common.py::build(variant=3)`](../results/fitc10_campaign/scripts/common.py)
on top of `build_A.build(..., vth="065")` with base netlist
[`rev10/sim/circuits/t5L_x2_v065.cir`](../rev10/sim/circuits/t5L_x2_v065.cir) (a byte copy of `t5L_x2_v085.cir` with
only the `.lib` line changed to `fitc10`; [D2](../results/fitc10_campaign/DECISIONS.md)).

| Change | Base design | Variant 3 | Decision |
|---|---|---|---|
| Rail capacitors CRAIL1–5 | 375 pF | **2201.25 pF** (×5.87, the mobility ratio) | [D3](../results/fitc10_campaign/DECISIONS.md) |
| Reference capacitor CREF | 24 pF | **140.88 pF** (×5.87) | [D9, D11](../results/fitc10_campaign/DECISIONS.md) |
| Every TFT with drain = 0 **and** gate = 0 (19 devices) | — | **L ×6, W unchanged** | [D4](../results/fitc10_campaign/DECISIONS.md) |
| Host row levels | V₁ 1.62 / V₂ 2.20 V (at 0.85 V) | formula at 0.65 V: **V₁ 1.82 / V₂ 2.40 V** | [D2](../results/fitc10_campaign/DECISIONS.md) |
| Race window (simulation setting) | 900 µs (`build_A` default) | 2500 µs after C2 (`.tran` to 3008 µs) | [D6 amendment](../results/fitc10_campaign/DECISIONS.md) |

The 19 loads made 6× longer ([D4](../results/fitc10_campaign/DECISIONS.md)):

| Device | Role | W (µm) | L before → after (µm) |
|---|---|---|---|
| X62 | self-biased pull-down (servo) | 20 | 10 → 60 |
| X64 | tracking load (servo) | 33 | 10 → 60 |
| X80 | idle pull-down of `win` | 5 | 20 → 120 |
| XI2 | inverter load (`lockb`) | 10 | 5 → 30 |
| X82, X92, X102, X112, X122 | detect loads (`d1–5`) | 20 | 20 → 120 |
| X84, X94, X104, X114, X124 | latch load A (`na1–5`) | 10 | 20 → 120 |
| X87, X97, X107, X117, X127 | latch load B (`nb1–5`) | 20 | 5 → 30 |

How Variant 3 was chosen: it is a **rebuild from the author's decisions**, not a recovered copy of the lost
`fitc10` netlist. Variant 3 was adopted **after** the Variant 1 and Variant 3 Gate B data had been seen (D11), with the
criterion "race time consistent with the original ≈ 800 µs". Variant 1 (CREF 24 pF) is kept as a measured CREF
sensitivity: it gave 90/90 identical outcomes with a longer race
([fitc10 summary/v1_vs_v3.json](../results/fitc10_campaign/summary/v1_vs_v3.json)).

### 2.3 TFT count
**134 TFT instances** in the nominal netlist (`grep -c '^X' docs/rev10_1_nominal.cir`; also `n_tft` in
[fitc10 summary/v3/phase1_runs.csv](../results/fitc10_campaign/summary/v3/phase1_runs.csv)):

| Block | Instances | Count |
|---|---|---|
| Crossbar banks (non-empty, `potftseg`) | X1–X30 minus 9 empty | 21 |
| Dummy calibration columns | X31–X60 | 30 |
| Drift servo | X61–X64 | 4 |
| Level-shift bias and follower | X65, X66 | 2 |
| Sampler, dummy, CREF reset | X67–X69 | 3 |
| Dummy-column steering | X70–X74 | 5 |
| Rail reset switches | X75–X79 | 5 |
| `win` pull-down, inverter, `win` precharge | X80, XI1, XI2, XWR | 4 |
| Per class: comparator (3), latch (4: X84–X87), `nb` reset (X88), lock (X89), `win` driver (X90) | X81–X130 | 50 |
| Latch-history equaliser | XNP1–XNP5 | 5 |
| Spares (gate tied to VDD, off) | X141–X145 | 5 |
| **Total** | | **134** = 113 fixed + 21 crossbar banks |

The 113 + banks relation is from [weights_schemeA DECISIONS W1.3](../results/weights_schemeA/DECISIONS.md).

### 2.4 Builder and canonical netlist
- **Builder chain:** `rev10/sim/tools/build_A.py` (frozen base-design builder; built on `build_final.py` → `t11.py` →
  `t10.py` → `t8.py` → `t6fix.py` + `lockvar.py`) → `results/fitc10_campaign/scripts/common.py::build(variant=3)`
  (Variant 3 resize). Later campaigns wrap the same call: `energy_host/scripts/eh.py::build` (byte-identical,
  [check_build.json](../results/energy_host/summary/check_build.json)), `host_v2/scripts/hv2.py::build_cls` (v2 host
  stimuli), `host_v21/scripts/hv21.py::run_cls` (v2.1 modes).
- **Canonical netlist:** [`docs/rev10_1_nominal.cir`](rev10_1_nominal.cir): Variant 3 die, `fitc10` nominal corner,
  weights `F_hw_m4_firstpass.npy`, input = test sample #81 (label class 5), warm start = the Variant 3 warm state
  `results/fitc10_campaign/raw/v3/warmstart/fitc10_warm`. Generated by script, never edited by hand:

  ```bash
  sh tools/setup_layout.sh
  python3 tools/gen_nominal_netlist.py           # writes docs/rev10_1_nominal.cir
  python3 tools/gen_nominal_netlist.py --check   # rebuilds and compares byte for byte
  ```

  SHA-256 `52ba7082b7f84c8eba42fdb6646cfa811e12d8f9d74abf915a77b7a4b938a18a`. It is byte-identical to the netlist the fitc10 campaign
  simulated for #81 in Phase 1 (`results/fitc10_campaign/raw/v3/phase1/s81.cir.gz`; compared when this
  netlist was created; the simulated netlists are not included in this release).
- **What the file contains:** the die (all `X`, `C`, `R` elements) is the Tortoise v1.0 die. Its **host sources are the v1
  stimuli** (warm start via `.ic`, `rstb` released at 150 µs, 2500 µs race window), because that is what the shared
  builder emits. The v2.1 stimuli (cold power-up or warm mode W, `rstb` at 50 µs, k-scaling, early end) are added by
  `hv2.build_cls` / `hv21.run_cls` and specified in §4. The netlist's header comment lines (e.g. "Rev-4 Autonomous",
  "145-TFT budget", "Zero hidden subcircuits") are inherited from the base netlist text of an earlier design iteration and are **not** accurate
  for Tortoise v1.0; they were left unchanged so the file stays identical to the builder output.
- **How to run it:** the includes are relative (`../models/...`), so it runs from a directory one level below
  `/home/claude/w/sim` after `sh tools/setup_layout.sh`, e.g.
  `cd /home/claude/w/sim/circuits && cp $REPO/docs/rev10_1_nominal.cir . && RELAX=1 python3 ../tools/run_diag.py rev10_1_nominal.cir nom81`.
  Use the lab-corner `RELAX=1` solver set ([`docs/TOOLING.md`](TOOLING.md) §6).

---

## 3. Weights

`rev10/eval/F_hw_m4_firstpass.npy` (SHA-256 `263db5304ea674e1f1d858515f8e826c2441a505c2588409527fc8998b28c840`),
integer fingers F[i, k] (row i = input, column k = class), 60 fingers per column, 21 non-empty banks:

| input \ class | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| 1 (pH) | 9 | 0 | 26 | 29 | 5 |
| 2 (uric acid) | 0 | 21 | 3 | 12 | 0 |
| 3 (lactate) | 4 | 5 | 0 | 0 | 28 |
| 4 (temperature) | 0 | 17 | 8 | 0 | 19 |
| 5 (pyocyanin) | 9 | 0 | 6 | 19 | 6 |
| 6 (impedance) | 38 | 17 | 17 | 0 | 2 |
| column sum | 60 | 60 | 60 | 60 | 60 |

These are hardware-aware weights retrained for the base design under the **old pulse law**, not for scheme A
([`docs/TOOLING.md`](TOOLING.md) §7 item 3; [fitc10 REPORT §4](../results/fitc10_campaign/REPORT.md)).
How they were originally selected is not recorded beyond "the author's choice"
([weights_schemeA REPORT §8](../results/weights_schemeA/REPORT.md)).

**Why they are kept over the weight-retraining study's candidate (`cand_a`, `results/weights_schemeA/weights/FINAL_frozen.npy`).**
The scheme-A retraining campaign found no evidence that retrained weights are better:
- Test accuracy is the same: 62/90 for both; paired 6 gained, 6 lost, exact McNemar p = 1.0
  ([A2_FINAL_frozen.json](../results/weights_schemeA/summary/A2_FINAL_frozen.json)).
- Validity is lower with `cand_a`: 82/90 vs 87/90, from more near-tie double latches (8 vs 3)
  ([A2_FINAL_frozen.json](../results/weights_schemeA/summary/A2_FINAL_frozen.json)).
- On the 40 held-out selection samples the old weights scored 26/40 against 25/40 for every candidate
  ([A1_select.json](../results/weights_schemeA/summary/A1_select.json)).
- Under size-scaled mismatch `cand_a` is ahead by 2 and 4 of 100 (66 vs 64, 61 vs 57), not significant (paired
  p = 0.845 / 0.503) ([A3_FINAL_frozen.json](../results/weights_schemeA/summary/A3_FINAL_frozen.json)).
- The ceiling analysis explains why: a float linear classifier reaches 73.7 % in CV, the crossbar's bias-free,
  equal-column-sum form 67.9 % ([A0_ceilings.json](../results/weights_schemeA/summary/A0_ceilings.json)).
- Every later campaign (energy/host, host v2, host v2.1) was run with the old weights, so all protocol results in §4–§5
  apply to them only. The campaign's own recommendation is the same ([weights_schemeA REPORT §9 item 5](../results/weights_schemeA/REPORT.md)).

---

## 4. Host protocol v2.1 (for a host-firmware implementer)

### 4.1 Interface
The die has one supply and ten host-driven lines, and five outputs. **The host uses only:** its own line levels and
timer, the five class outputs `na1–5`, and a current meter on its own VDD supply (I_DD). It never uses the die's true
|V_th| or µ ([host_v2 H2](../results/host_v2/DECISIONS.md), [host_v21 P2](../results/host_v21/DECISIONS.md)).

| Line | Driven by host | Levels | Idle level (end of a classification) |
|---|---|---|---|
| `VDD` | supply (switched in mode G) | 0 / 3.3 V | 3.3 V (mode W); 0 V (mode G, gated) |
| `row1`–`row6` | 6 analog drivers | 3.3 V (inactive), V₁, V₂; ramp 3.3 → 1.3 V during a1 | 3.3 V |
| `rstr` | digital | 0 / 3.3 V | 3.3 V |
| `rstb` | digital | 0 / 3.3 V | 3.3 V |
| `phib` | digital | 0 / 3.3 V | 3.3 V |
| `phi` | digital, complement of `phib` | 0 / 3.3 V | 0 V |
| `na1`–`na5` (outputs) | read by host | logic threshold **1.65 V**; "latched" **> 2.5 V** | — |
| I_DD | host meter on its VDD supply | µA resolution assumed (noise-free in simulation) | — |

Idle levels are from [energy_host DECISIONS E2](../results/energy_host/DECISIONS.md) and
[host_v21 DECISIONS P2.3 step 4](../results/host_v21/DECISIONS.md). The input vector x ∈ [0, 1]⁶ is normalised by the
host before the classification (dataset: [`data/trace2_data.npz`](../data/trace2_data.npz), synthetic).

### 4.2 Constants

| Symbol | Value | Meaning | Source |
|---|---|---|---|
| T₁ | 170 µs (× k) | C1 time per unit input | H2.2 step 4 |
| WMIN | 20 µs (not scaled) | C1 pedestal per row | H2.2 step 4 |
| GAP | 5 µs | all rows off between C1 and C2 | H2.2 step 4 |
| reset length | 300 µs × k (e = 300·(k − 1)) | reset phase | H2.2 |
| `rstb` release | 50 µs (not scaled) | latch precharge end | H2.2 step 2, P2.3 step 2 |
| t_on | 320 + e µs | start of output watch | H2.2 step 6 |
| D | 50·k µs | early-end delay (integrating timer) | H2.2 step 6, H4.2 |
| READ | 10·k µs | rows-off → read | H2.2 step 6 |
| timeout | 4000·k µs after C2 start | no result | H2.2 step 7 |
| k | clip(1/µ̂, 1.0, 2.5) | mobility compensation | H2.1 step 5 |
| c_a1 | −50.883 mV | a1 offset (nominal die) | [design_constants.json](../results/host_v2/summary/design_constants.json) |
| I_ref | 31.439 µA | ΔI_DD at V_raw + 0.6 V on the nominal die | [design_constants.json](../results/host_v2/summary/design_constants.json) |
| c_race (mode G) | −34.481 mV | race cross-check offset | [design_constants.json](../results/host_v2/summary/design_constants.json) |
| c_race,W (mode W) | −8.054 mV | race cross-check offset, warm sequence | [design_constants_W.json](../results/host_v21/summary/design_constants_W.json) |
| flag band | 50 mV | \|V̂_race − V̂\| above this flags | H2.1 step 4 |
| V_gate | 0.600 V | mode W if V̂ < V_gate | P2.0 |
| T_off / T_idle | 1 s | between classifications (both modes) | H1-outcome 1, P2 |
| power-up / power-down ramp | 10 µs linear (tested 1–100 µs, §4.6) | mode G | H2.2 steps 1, 8; P3.5 |

### 4.3 Formulas
- **Row levels:** V₁ = 3.3 − V̂ − 0.83 V (calibration and C1), V₂ = 3.3 − V̂ − 0.25 V (C2), rounded to 1 mV.
  At V̂ = 0.65 V: 1.82 / 2.40 V.
- **a1 |V_th| estimate:** V_raw from the three V_SG values where ΔI_DD = 5, 20, 45 µA (first crossing, linear
  interpolation), solving √I = a(V_SG − V − I·R) exactly for (a, V, R); **V̂ = V_raw − c_a1**.
- **µ estimate:** µ̂ = ΔI_DD(V_SG = V_raw + 0.6 V) / I_ref.
- **Race cross-check:** r = √(t_b/t_a), A = 3.3 − V₂a, B = 3.3 − V₂b, V̂_race = (r·B − A)/(r − 1) − c_race (c_race,W in
  mode W). Flag if a time is missing or |V̂_race − V̂| > 50 mV. **A flag is reported; it does not change the levels.**
- **Mode:** W if V̂ < 0.600 V, else G. Decided once per calibration session.
- **C1 on-time of row i:** WMIN + x_i·T₁·k = 20 + 170·k·x_i µs.
- **C2 start:** t_C2 = t₀ + 20 + 170·k + 5 µs with t₀ = 312.5 + e µs (at k = 1: 507.5 µs).

### 4.4 Timing tables (µs, from the start of a classification; e = 300·(k − 1); edges 1 µs unless stated)

| Line | Mode G (gated; = v2) | Mode W (VDD on) |
|---|---|---|
| `VDD` | ramp 0 → 3.3 V over 0–10, then 3.3 V | 3.3 V throughout (no power-up) |
| rows | ramp 0 → 3.3 V over 0–10; 3.3 V until 301 + e | 3.3 V until 301 + e |
| `phi` | ramp 0 → 3.3 V over 0–10; complement of `phib` | complement of `phib` |
| `rstr` | 0 V from t = 0 to 311.5 + e; 3.3 V by 312.5 + e | 3.3 → 0 V over 0–20; low until 311.5 + e; 3.3 V by 312.5 + e |
| `rstb` | 0 V until 50; 3.3 V by 51 | 0 V from t = 0 until 50; 3.3 V by 51 |
| `phib` | 0 V until 309 + e; 3.3 V by 310 + e | same |
| calibration (sampling `ref`) | all rows at V₁ from 302 + e to 310 + e | same |
| C1 | from t₀ = 312.5 + e: row i at V₁ for 20 + 170·k·x_i (0.2 µs edges), once; then 3.3 V | same |
| gap | all rows 3.3 V for 5 | same |
| C2 | from t_C2: all rows at V₂ (0.2 µs edge) | same |
| output watch | from 320 + e (integrating timer, §4.5) | same |
| end | rows → 3.3 V when the timer reaches 50·k; read 10·k later; then power-down (10 µs ramp of every source to 0 V) and 1 s off | rows → 3.3 V at the early end; read 10·k later; then 1 s idle with VDD on, every line at its idle level |

### 4.5 The early-end rule (accumulated time above 1.65 V)
The host does **not** react to "the first output edge". It integrates: from 320 + e µs it counts the **accumulated
time during which any of `na1–5` is above 1.65 V**; when that count reaches **50·k µs** it returns every row to 3.3 V
(0.2 µs edge) and **reads the outputs 0.2 + 10·k µs later**. Result = the classes with `na` > 2.5 V at the read.
**Valid** = exactly one class latched and it is the first output that rose; otherwise one of the failure labels
`timeout`, `none_latched`, `multi_latched`, `lockout_failed`, `latched_not_first`, `stuck_latched`. No output by
t_C2 + 4000·k µs → `timeout`. This is the rule as simulated and frozen ([host_v2 H4.2](../results/host_v2/DECISIONS.md));
a literal "first output" host behaves differently whenever an `na` is still decaying through 1.65 V at 320 + e µs
(it would have aborted every v2 run at 0.59 and 0.61 V; [host_v2 REPORT §8](../results/host_v2/REPORT.md)).

### 4.6 Power gating and ramp specification
- **Mode G:** after the read, VDD and every line ramp to 0 V over **10 µs** and stay off **1 s**; the next
  classification powers up with a 10 µs ramp of VDD, rows and `phi` from that 1 s-off state. Standby energy is 0
  (energy returned during power-down is not credited).
- **Ramp range tested:** 0.1×–10× the 10 µs ramp, i.e. **1 µs to 100 µs** (0.033–3.3 V/µs), applied to both power-up
  and power-down: **0 of 134 TFTs above 3.5 V at every tested rate**; worst device 3.436 V at 1 µs (XWR,
  margin 0.064 V) ([e2_ramp.json](../results/host_v21/summary/e2_ramp.json)). Faster than 1 µs or slower than 100 µs
  was not tested; protocol timing (e.g. `rstb` at 50 µs) was **not** scaled with the ramp.
- **Implementer rule:** keep power-up and power-down ramps between 1 and 100 µs, linear, common to VDD, rows and
  `phi` (power-up) and to every source (power-down), as simulated. A ramp near 1 µs leaves 64 mV of stress margin
  through `win` overshoot; prefer ≥ 3 µs (worst 3.374 V at 3.33 µs) ([e2_ramp.json](../results/host_v21/summary/e2_ramp.json)).
- **Negative nodes:** power-down drives `na`, `nb`, `lockb` to ≈ −2.2 V at every tested rate, and the next power-up
  starts from ≈ −2.04 V ([e2_ramp.json](../results/host_v21/summary/e2_ramp.json),
  [c2_stress.json](../results/host_v2/summary/c2_stress.json)). Sequenced supplies were not tried.
- **Mode W:** no power cycling between classifications; VDD stays at 3.3 V and standby is paid (§5).
- **Idle length:** exactly 1 s was simulated. Other idle lengths change the start state (rails 0.62 V after 1 ms,
  0.11 V after 10 s; [host_v2 DECISIONS H1-outcome 1](../results/host_v2/DECISIONS.md)) and were not evaluated.

### 4.7 Firmware outline (restates §4.2–4.6; the frozen text in §4.8 governs)
```
calibrate(die):                              # once per die / condition; re-run to re-trim
    hold every line and VDD at 0 V for a long time
    a1: power up (10 us ramp), rstr = 0 from t = 0, rstb low until 50 us, phib low until 290 us,
        rows 3.3 V until 300 us then linear ramp to 1.3 V at 4300 us, back to 3.3 V at 4301 us
        I0 = mean I_DD over 293-300 us; dI = I_DD - I0; V_SG = 3.3 - row level
        V_raw = 3-point fit at dI = 5, 20, 45 uA          # fail if any crossing is missing
        V_hat = V_raw - c_a1 ; mu_hat = dI(V_raw + 0.6 V) / I_ref
    mode = W if V_hat < 0.600 else G
    V1 = round(3.3 - V_hat - 0.83, 3) ; k = clip(1 / mu_hat, 1.0, 2.5)
    for ov in (0.45, 0.30):                      # cross-check races, input x = 0
        idle(mode, 1 s); t[ov] = classify(x = 0, V1, V2 = 3.3 - V_hat - ov, k, mode).first_edge_after_C2
    V_hat_race = race formula (c_race of the mode); flag = missing time or |V_hat_race - V_hat| > 50 mV  # report only
    idle(mode, 1 s)
    store V1, V2 = round(3.3 - V_hat - 0.25, 3), k, mode

classify(x):  per §4.4 timing table for the stored mode, early end per §4.5, then idle(mode, 1 s)
```

### 4.8 Frozen protocol text (verbatim)
The following is copied verbatim from the frozen decision records; section numbers and file paths in it refer to
those records. Paths such as `scripts/hv2.py` are relative to `results/host_v2/` and `results/host_v21/`.

**From [`results/host_v2/DECISIONS.md`](../results/host_v2/DECISIONS.md), H2 (frozen 2026-10-28, commit `8948461`):**

> ## H2. HOST PROTOCOL v2 (FROZEN 2026-10-28; changes only as dated deviations in H4)
> Implementation: `scripts/hv2.py` (constants at its top), `scripts/phases.py`. Times in µs. The host uses only: its own
> line levels and timer, the five class outputs `na1–5` (logic threshold 1.65 V, "latched" > 2.5 V), and a current meter
> on its own VDD supply (I_DD). The simulator's |V_th| and µ are used only in runs labelled **ideal**.
>
> ### H2.1 Calibration session (once per die/condition, before its classifications; re-run whenever a re-trim is wanted)
> 1. **Start:** die unpowered for a long time (simulated as every node at 0 V).
> 2. **a1, supply-current transfer:** 0–10 µs VDD, rows and `phi` ramp 0 → 3.3 V; `rstr` 0 V from t = 0 (rails clamped by
>    the reset switches, latches held), back to 3.3 V at 4302–4303; `rstb` 0 V until 50, 3.3 V from 51; `phib` 0 V until
>    290, 3.3 V from 291 (`phi` the complement); rows 3.3 V until 300, linear ramp to 1.3 V at 4300, back to 3.3 V at
>    4301. ΔI = I_DD − mean I_DD over 293–300. V_SG = 3.3 V − row level.
>    - V_raw: V_SG at ΔI = 5, 20, 45 µA (first crossing, linear interpolation), exact solve of √I = a(V_SG − V − I·R).
>    - **V̂ = V_raw − c_a1**, c_a1 = **−50.883 mV** (nominal die, design-time, `summary/design_constants.json`).
>    - **µ̂ = ΔI(V_SG = V_raw + 0.6 V) / I_ref**, I_ref = **31.439 µA** (nominal die). If any crossing is missing the
>      calibration fails (reported; the die is not classified with learned values).
> 3. VDD and all lines off (10 µs ramp to 0 V), **1 s**.
> 4. **Race-timing cross-check:** two classifications (H2.2) with input x = 0 and the learned V₁, k, and
>    V₂ = 3.3 − V̂ − 0.45 (race a) and 3.3 − V̂ − 0.30 (race b), each followed by 1 s off. The host times the first
>    output edge from the start of C2 (t_a, t_b). V̂_race = (r·B − A)/(r − 1) − c_race, r = √(t_b/t_a), A = 3.3 − V₂a,
>    B = 3.3 − V₂b, c_race = **−34.481 mV** (nominal die). **Flag** if a time is missing or |V̂_race − V̂| > 50 mV. A flag
>    is reported; it does not change the levels (a1 is the primary estimate).
> 5. **Learned values:** V₁ = 3.3 − V̂ − 0.83, V₂ = 3.3 − V̂ − 0.25 (rounded to 1 mV); **k = clip(1/µ̂, 1.0, 2.5)**.
> 6. The state after the 1 s off that follows race b is the start state of the first classification.
>
> ### H2.2 Classification (every classification; e = 300·(k − 1))
> 1. **Power-up** from the 1 s-off state: 0–10 µs VDD, rows and `phi` ramp 0 → protocol level.
> 2. **Reset:** `rstr` 0 V from t = 0 to 311.5 + e, 3.3 V by 312.5 + e. **`rstb` 0 V until 50, 3.3 V by 51 (not scaled).**
>    `phib` 0 V until 309 + e, 3.3 V by 310 + e (`phi` the complement). Rows 3.3 V until 301 + e. (reset length 300·k)
> 3. **Sampling/calibration** (not scaled): rows at V₁ from 302 + e to 310 + e (1 µs edges).
> 4. **C1** from t₀ = 312.5 + e: row i at V₁ for 20 + x_i·170·k (WMIN 20 µs not scaled), all rows off 5 µs.
> 5. **C2** from t_C2 = t₀ + 20 + 170·k + 5: all rows at V₂.
> 6. **Early end:** the host watches `na1–5` from 320 + e. At the first output > 1.65 V (time t_f) it waits **50·k**, returns
>    every row to 3.3 V (0.2 µs edge) and **reads the outputs 10·k later**. Result = the classes with `na` > 2.5 V at the
>    read. **Valid** = exactly one class latched and it is the first output that rose; otherwise the failure label
>    (`timeout`, `none_latched`, `multi_latched`, `lockout_failed`, `latched_not_first`, `stuck_latched`).
> 7. **Timeout:** no output by t_C2 + **4000·k** → no result (`timeout`).
> 8. **Power gating:** after the read, VDD and all lines → 0 V (10 µs ramp); off **1 s** before the next classification.
> 9. Energy per classification = Σ over the 11 sources of ∫ v·i dt from t = 0 to the read time (energy/host study E1 definition);
>    standby = 0 (no source is on); energy returned during the power-down is not credited.
>
> ### H2.3 Reference policies (labelled)
> - **ideal:** H2.2 with V̂ = true |V_th| and k = clip(1/µ_true, 1, 2.5), same start state as the learned runs.
> - **v1** (energy/host study "baseline"): VDD on, warm start (Variant 3 warm state), `rstb` 150 µs, 300 µs reset, T₁ 170,
>   2500 µs window, levels fixed (1.82/2.40 V) or ideal re-trim. Existing v1 runs are reused, not re-simulated.

**From [`results/host_v2/DECISIONS.md`](../results/host_v2/DECISIONS.md), deviation H4.2 (the early-end timer, part of v2):**

> - **H4.2 (2026-10-29 ≈ 02:10 UTC) — the early-end timer, as simulated.** H2.2 step 6 says the host waits 50·k µs "at the
>   first output > 1.65 V". The host model in every v2 run (inherited from the energy/host study's O1/O12) is an integrator: it counts
>   the **accumulated time during which any output is above 1.65 V** (from 320 + e µs) and returns the rows to 3.3 V when
>   that count reaches 50·k µs; the read follows 0.2 + 10·k µs later. The two agree whenever every `na` is below 1.65 V
>   when counting starts and the first output stays high (all C1/C2/C5 runs and all but one C3 run so far). They differ
>   when an `na` is still decaying through 1.65 V at 320 + e µs (found in C6 diagnostics; mismatch die d04; low |V_th|):
>   the integrator counts that time, so the rows go off earlier after the real trip; a literal "first output" host would
>   instead end the race at 320 + e + 50·k µs. **Decision:** the integrator is the v2 rule (it is what was simulated and
>   frozen in code). The metric's read time is corrected to the simulated one (t_read = rows-off + 0.2 + READ =
>   stop time − 5 µs) in `metrics_v2`, and `scripts/read_fix.py` recomputes the read-time outcome of earlier runs from
>   their 1 µs waveforms where the stored read time is later than (stop time − 5 µs) by more than 0.15 µs (one time step of `stop when` overshoot) (the old values are kept in the JSON as `read_fix`).
>   **Applied 02:30 UTC: 0 of 440 finished classification runs changed** (C1, C2 chain step, C3 so far, C5; the largest
>   pre-trip count among them is 0.05 µs, C3 0.65 V/µ ×1 #60, below the 0.15 µs tolerance). A first pass of `read_fix.py`
>   with a 0.01 µs tolerance rewrote 393 JSONs by ≤ 0.1 µs (the `stop when` overshoot) with no outcome change; it was
>   reverted the same minute. **Affects:** the d04 calibration races (6 µs; race times unaffected), the C6 calibration
>   races (stuck, failing under either reading), and any later C4/C6 run with a pre-trip high `na`; the report gives, for
>   C6 and C4, how many runs a literal-"first output" host would have aborted.
>   Final check (05:20 UTC): `read_fix.py` over all 500 C3, 100 C4 and 180 C6/C6b runs changed 0 (C4 and C6 ran with the
>   corrected metric; their pre-trip counts are in each JSON as `host_timer_pre_trip_us`: d04 6.1 µs on 20/20 runs,
>   C6b 26.6 / 13.2 / 2.1 µs at 0.57 / 0.59 / 0.61 V).

**From [`results/host_v21/DECISIONS.md`](../results/host_v21/DECISIONS.md), P2 (frozen 2026-10-29, commit `1db5914`):**

> ## P2. HOST PROTOCOL v2.1 (FROZEN 2026-10-29; changes only as dated deviations in P4)
> Implementation: `scripts/hv21.py` (constants at its top), `scripts/phases21.py`. Times in µs. The host uses only: its
> own line levels and timer, the five class outputs `na1–5` (logic threshold 1.65 V, "latched" > 2.5 V), and a current
> meter on its own VDD supply (I_DD). Simulator |V_th| and µ are used only in runs labelled **forced** (mode choice) or
> **ideal** (none planned).
>
> **v2.1 = v2 + adaptive power gating.** Everything in v2 H2 (a1 calibration, V̂ and µ̂ estimators, levels, k, reset
> extension, T₁, early end with the integrating timer of H4.2, timeout 4000·k, read rule, failure labels) is unchanged.
> New: the host chooses, once per calibration session, between two modes from its own |V_th| estimate.
>
> ### P2.0 Mode rule and threshold
> - **Mode W (VDD on)** if **V̂ < V_gate = 0.600 V**; otherwise **mode G (gated) = v2 exactly.**
> - **Derivation from the v2 C6/C6b data** (`host_v2/summary/c6_lower_edge.json`, per-run `host_timer_pre_trip_us`,
>   `host_v2/raw/cal/*/calibration.json`):
>   - v2 outcomes (20 samples each): ≤ 0.55 V 0/20 (`stuck_latched` 20/20); **0.57 V 0/20 (`none_latched` 20/20; the
>     host timer counted 26.6 µs before the real trip)**; **0.59 V 15/20** (13.1–13.3 µs counted before the trip);
>     0.61 V 15/20 (2.0–2.1 µs counted). The short-run diagnostic puts the stuck edge at 0.59/0.60 V. The lowest
>     |V_th| at which v2 was observed to classify at the nominal rate is **0.59 V**, and it does so with a 13 µs
>     pre-trip count against D = 50 µs (thin).
>   - Host estimate error: over all 39 v2 calibration sessions (C3, C4, C6) the a1 error V̂ − |V_th| is **−4.4 … +8.5 mV**.
>   - **V_gate = 0.59 V + 8.5 mV = 0.5985 V, rounded up to 0.600 V.** With errors as in v2, a die runs mode G only if its
>     true |V_th| ≥ 0.600 − 0.0085 = 0.5915 V, above the lowest point where v2 worked. Dies whose estimate falls below
>     0.600 V (true |V_th| up to ≈ 0.600 + 0.0044 = 0.6044 V) run mode W, so mode W must also work just above the
>     threshold: tested with a forced-W reference at 0.61 V (P3.2).
>   - Expected from the (deterministic, unchanged) a1: the v2 estimates were 0.4936 / 0.5131 / 0.5325 / 0.5518 / 0.5719 /
>     **0.5940 / 0.6064 V** at 0.49 … 0.61 V, so 0.49–0.59 V are expected in mode W and 0.61 V in mode G. Recorded here
>     as a prediction; the mode is whatever each v2.1 calibration session decides.
>
> ### P2.1 Calibration session (once per die/condition)
> 1. Start: die unpowered for a long time (every node 0 V). **a1 exactly as v2 H2.1 step 2** (cold power-up, `rstr` low,
>    4.3 ms row ramp), V̂ = V_raw − c_a1, µ̂ = ΔI_DD(V_raw + 0.6 V)/I_ref (v2 design constants). Missing crossing → the
>    calibration fails (as v2). **Mode decision (P2.0)** from V̂.
> 2. Mode G: v2 H2.1 steps 3–6 unchanged (1 s off → race a → 1 s off → race b → 1 s off → start state), c_race = −34.481 mV.
> 3. Mode W: VDD stays on. The a1 ends with every line at its idle level (rows, `rstr`, `rstb`, `phib` 3.3 V, `phi` 0 V);
>    **1 s idle with VDD on** → race a → 1 s idle → race b → 1 s idle → start state of the first classification. Races are
>    mode-W classifications (P2.3) with x = 0 and v2's race levels (V₂ = 3.3 − V̂ − 0.45 / − 0.30, learned V₁, k).
>    Cross-check as v2 with **c_race,W = −8.054 mV** (P1.2); flag if a time is missing or |V̂_race − V̂| > 50 mV; a flag
>    is reported and changes nothing.
> 4. Learned values as v2: V₁ = 3.3 − V̂ − 0.83, V₂ = 3.3 − V̂ − 0.25 (1 mV), k = clip(1/µ̂, 1, 2.5).
>
> ### P2.2 Classification, mode G
> v2 H2.2 steps 1–9 unchanged: power-up ramp 0–10 µs from the 1 s-off state, `rstb` 0 V until 50 µs, …, power gating
> (VDD and every line → 0 V over 10 µs, off 1 s). Standby energy 0.
>
> ### P2.3 Classification, mode W (e = 300·(k − 1))
> 1. **No power-up:** VDD 3.3 V throughout; the classification starts from the state at the end of the previous 1 s idle
>    (simulated as `.ic` of the saved state nodes, VDD on).
> 2. Reset (energy/host study v1 timing **with the v1 `rstb` fix**): `rstr` 3.3 → 0 V over 0–20, low until 311.5 + e, 3.3 V by
>    312.5 + e; **`rstb` 0 V from t = 0 until 50, 3.3 V by 51** (not scaled); `phib` 0 V until 309 + e, 3.3 V by 310 + e
>    (`phi` the complement); rows 3.3 V until 301 + e.
> 3. Sampling, C1, C2, early end (integrating timer from 320 + e, D = 50·k, READ = 10·k), timeout 4000·k, read rule,
>    validity and failure labels: **as v2 H2.2 steps 3–7 and H4.2.**
> 4. After the read: VDD stays at 3.3 V and every line is at its idle level (rows return to 3.3 V at the early end;
>    `rstr`, `rstb`, `phib` are already 3.3 V, `phi` 0 V); **idle 1 s**, then the next classification.
>
> ### P2.4 Energy and standby accounting
> - Energy per classification (both modes) = Σ over the 11 sources of ∫ v·i dt from t = 0 to the read time (v2 H2.2.9).
> - **Standby** (mode W): the 1 s idle after a classification, simulated from its read state, all 11 sources; reported as
>   mean power over the 1 s, power at 1 ms and 1 s, and idle energy. Mode G: standby 0 (every source at 0 V; the 10 µs
>   power-down's energy is not credited, as in v2). Per classification at 1 /s = classification energy + idle energy.

---

## 5. Operating envelope

N = 20 means the fixed 20-sample test subset
([phase3_subset.json](../results/fitc10_campaign/summary/phase3_subset.json), 4 per class); one sample is 5 points.
Global corners only (uniform |V_th| shift and µ factor); aging inputs are **literature proxies**. Nominal reference on
the same 20 samples: 15/20. "correct / valid of N".

### 5.1 Tortoise v1.0 (host protocol v2.1; mode G above V̂ = 0.600 V, mode W below)

**|V_th| × µ, no mismatch** (each cell its own calibration session, learned levels and k):

| \|V_th\| \ µ | ×1 | ×0.85 | ×0.7 | ×0.6 | ×0.5 | Mode | Source |
|---|---|---|---|---|---|---|---|
| 0.49 V | **0 / 0 (FAIL: timeout 16, none_latched 4)** | not run | not run | not run | not run | W | [e1_lower_edge.json](../results/host_v21/summary/e1_lower_edge.json) |
| 0.51 V | 15 / 20 | not run | not run | not run | not run | W | [e1_lower_edge.json](../results/host_v21/summary/e1_lower_edge.json) |
| 0.53 V | 15 / 20 | not run | not run | not run | not run | W | same |
| 0.55 V | 15 / 20 | not run | not run | not run | not run | W | same |
| 0.57 V | 15 / 20 | not run | not run | not run | not run | W | same |
| 0.59 V | 15 / 20 | not run | not run | not run | not run | W | same |
| 0.61 V | 15 / 20 | not run | not run | not run | not run | G | same |
| 0.65 V (nominal) | 15 / 20 | 15 / 20 | 15 / 20 | 15 / 20 | 15 / 20 | G | [c3_aging.json](../results/host_v2/summary/c3_aging.json) |
| 0.75 V | 15 / 20 | 15 / 20 | 15 / 20 | 15 / 20 | 15 / 20 | G | same |
| 0.85 V | 14 / 19 | 14 / 19 | 14 / 19 | 14 / 19 | 15 / 20 | G | same |
| 0.95 V | 13 / 18 | 13 / 18 | 13 / 18 | 13 / 18 | 13 / 18 | G | same |
| 1.00 V | 13 / 18 | 13 / 18 | 13 / 18 | 13 / 18 | 13 / 18 (calibration flagged; ideal knowledge gives the same 13/18) | G | same |
| > 1.00 V | not run under v2/v2.1 | | | | | | — |

Pooled over the 25-cell aging grid (0.65–1.00 V × µ ×1–×0.5): **351/500 = 70.2 %** (Wilson 66.1–74.0 %), validity
476/500 ([c3_aging.json](../results/host_v2/summary/c3_aging.json)). The rows 0.65–1.00 V are host protocol **v2**
runs; v2.1 is v2 exactly whenever V̂ ≥ 0.600 V (P2.0), and the v2.1 rerun at 0.61 V reproduced v2 on 20/20 outcomes
and race times ([e1_lower_edge.json](../results/host_v21/summary/e1_lower_edge.json)).

**Other conditions under v2 / v2.1:**

| Condition | Result | N | Source |
|---|---|---|---|
| Nominal die, all 90 test samples (v2) | 62/90 = 68.9 % (Wilson 58.7–77.5 %), valid 87/90; outcomes identical to v1 on 90/90 | 90 | [c1_nominal.json](../results/host_v2/summary/c1_nominal.json) |
| Size-scaled V_th mismatch, anchor 20 mV, 5 dies (v2, \|V_th\| 0.65 V) | 64/100 (54.2–72.7 %), valid 97/100 | 100 | [c4_mismatch.json](../results/host_v2/summary/c4_mismatch.json) |
| Mismatch at anchor 35 mV, flat σ, or with drift | **not run under v2/v2.1** (v1 results in §5.2) | — | — |
| History, mode G (chain 30–39, 1 s off) | 10/10 outcomes identical; trip shift ≤ 0.003 µs | 10 | [c1_nominal.json](../results/host_v2/summary/c1_nominal.json) |
| History, mode G at µ ×0.5 (20-step chain) | 20/20 outcomes identical | 20 | [c5_history.json](../results/host_v2/summary/c5_history.json) |
| History, mode W at 0.51 V (20-step chain, 1 s VDD-on idle) | 14/20 correct, 19/20 valid; 19/20 outcomes identical to independent runs (one near tie → double latch); races up to 19 µs longer | 20 | [e1_lower_edge.json](../results/host_v21/summary/e1_lower_edge.json) |
| Mode W at forced 0.61 V (estimate on the wrong side of V_gate) | 15/20, outcomes identical to mode G | 20 | [e1_lower_edge.json](../results/host_v21/summary/e1_lower_edge.json) |
| Mode W combined with µ loss, mismatch or aging | **not run** | — | — |
| Gate stress, 5 extreme runs, power-up + classification + power-down + 1 s off, ramps 1–100 µs | 0/134 TFTs > 3.5 V; worst 3.436 V (1 µs ramp); crossbar ≤ 3.05 V; nodes to ≈ −2.2 V | 5 per rate | [e2_ramp.json](../results/host_v21/summary/e2_ramp.json) |
| Energy per classification, mode G, nominal (v2) | median 588 nJ (499–655 nJ); standby 0 | 90 | [c1_nominal.json](../results/host_v2/summary/c1_nominal.json) |
| Energy per classification, mode W, 0.51–0.59 V | median 395–468 nJ, plus standby 174–192 µW during the 1 s idle (209 µW at 0.49 V) | 20 per point | [e1_lower_edge.json](../results/host_v21/summary/e1_lower_edge.json) |
| a1 \|V_th\| estimate error, aging grid | −4.4 … +8.5 mV; µ̂ −1 … +12 % (mostly high) | 25 cells | [c3_aging.json](../results/host_v2/summary/c3_aging.json) |

### 5.2 For comparison: the v1 protocol (warm start, fixed or ideal levels, 2500 µs window)
| Condition | Result | N | Source |
|---|---|---|---|
| Fixed levels (no re-trim): \|V_th\| 0.55 / 0.65 / 0.75 V | 14 / 15 / 13 of 20; 0/20 at 0.45 V (stuck latches) and at ≥ 0.85 V (timeouts) | 20 per point | [phase3A.json](../results/fitc10_campaign/summary/v3/phase3A.json) |
| Fixed levels: µ ×0.5 / ×0.75 / ×1.25 | 8 / 14 / 15 of 20 | 20 per point | [phase3A.json](../results/fitc10_campaign/summary/v3/phase3A.json) |
| Ideal re-trim: \|V_th\| 0.75 / 0.85 / 0.95 / 1.05 V | 15 / 14 / 13 / 11 of 20; strict (no trip in C1) 15 / 14 / 12 / 7 | 20 per point | [phase3A_T.json](../results/fitc10_campaign/summary/v3/phase3A_T.json) |
| Size-scaled V_th mismatch, anchor 20 / 35 mV | 64/100, 57/100 | 100 each | [phase3B_V.json](../results/fitc10_campaign/summary/v3/phase3B_V.json) |
| Flat σ_Vth 20 / 40 / 80 mV (+ σ_µ 10 %, σ_RC 20 %), worst-case bound | 39 / 41 / 31 of 100 | 100 each | [phase3B.json](../results/fitc10_campaign/summary/v3/phase3B.json) |
| Host level tolerance at 0.65 V (1D sweeps) | V₁ −175 … +100 mV, V₂ −25 … +75 mV within 5 points of nominal | 20 per point | [b2_retrim.json](../results/energy_host/summary/b2_retrim.json) |

---

## 6. Known failure modes and limits

1. **Lower |V_th| edge at 0.49–0.51 V.** v2.1 fails at 0.49 V (0/20: 16 timeouts, 4 `none_latched`) and works at
   0.51 V (15/20); the edge was bracketed by two 20-sample points, not bisected. The latches reset, but the
   comparator/latch swing is too weak to regenerate; no host timing tested fixes it, a circuit change would be needed
   ([e1_lower_edge.json](../results/host_v21/summary/e1_lower_edge.json), [host_v21 REPORT §3, §8](../results/host_v21/REPORT.md)).
   Under v2 alone (no mode W) the edge sits at 0.57–0.59 V ([c6_lower_edge.json](../results/host_v2/summary/c6_lower_edge.json)).
2. **Near-tie double latches are the main loss.** At nominal, all 3 invalid runs of 90 are double latches with
   runner-up gaps of 1.4–7.9 µs; the pass/fail boundary lies between 7.9 and 10.7 µs of gap, set by slow latch
   regeneration (`na` takes ≈ 25 µs from 1.4 to 3.1 V) rather than lock latency
   ([phase1.json](../results/fitc10_campaign/summary/v3/phase1.json), [fitc10 REPORT §3.2](../results/fitc10_campaign/REPORT.md)).
   Every failure in the v2 aging grid and under size-scaled mismatch is of this type
   ([c3_aging.json](../results/host_v2/summary/c3_aging.json), [c4_mismatch.json](../results/host_v2/summary/c4_mismatch.json)).
   A host could treat a double latch as "no decision" (not simulated).
3. **Negative internal nodes under power gating.** The 10 µs power-down drives `na`, `nb`, `lockb` to ≈ −2.2 V; they
   stay negative after 1 s, and the ramp rate does not remove them (1–100 µs tested). No device exceeds 3.5 V because
   of it in the audited runs, but the base design's rule "no negative voltages anywhere" no longer holds
   ([c2_stress.json](../results/host_v2/summary/c2_stress.json), [e2_ramp.json](../results/host_v21/summary/e2_ramp.json)).
4. **Thin stress margin at fast ramps.** At a 1 µs ramp the worst device reaches 3.436 V (margin 0.064 V, `win`
   overshoot on XWR); the trend 3.300 → 3.374 → 3.436 V at 10 / 3.33 / 1 µs suggests the limit is not far beyond 1 µs
   (a trend, not a result) ([e2_ramp.json](../results/host_v21/summary/e2_ramp.json)). Under power gating the crossbar
   margin falls to ≈ 0.47 V (3.03 V at the end of power-up) ([c2_stress.json](../results/host_v2/summary/c2_stress.json)).
5. **Mode W costs standby and brings history back.** Dies with V̂ < 0.600 V keep VDD on: 174–209 µW during the 1 s idle,
   ≈ 270–320× the energy of a gated die at 1 classification/s; a 20-step chain at 0.51 V changed one near-tie outcome
   ([e1_lower_edge.json](../results/host_v21/summary/e1_lower_edge.json)).
6. **The race cross-check gives false alarms at high |V_th|.** It reads +26 … +67 mV high at 0.95–1.00 V and flagged
   1.00 V / µ ×0.5, where a1 was off by only +6.6 mV ([c3_aging.json](../results/host_v2/summary/c3_aging.json)).
   The flag changes nothing in the protocol, but a host that acts on it would re-calibrate a good die.
7. **µ̂ is biased high** (up to +12 % at high |V_th| and low µ, because R_C does not scale with µ), so k can be up to
   ≈ 11 % short of 1/µ; it did not cost accuracy in the grid ([c3_aging.json](../results/host_v2/summary/c3_aging.json)).
8. **High |V_th| above 1.00 V** was not run under v2/v2.1. Under v1 with ideal re-trim, strong samples start tripping
   during integration from 0.95 V (2/20) and at 1.05 V (9/20, strict 7/20) because the window shrinks as
   ≈ V_DD − 2|V_th| ([phase3A_T.json](../results/fitc10_campaign/summary/v3/phase3A_T.json)).
9. **Accuracy is limited by the architecture.** The crossbar has no per-class bias; its best form reaches 67.9 % in
   training CV against 73.7 % for a general linear classifier, and retraining did not raise test accuracy
   ([A0_ceilings.json](../results/weights_schemeA/summary/A0_ceilings.json), [A2_FINAL_frozen.json](../results/weights_schemeA/summary/A2_FINAL_frozen.json)).
10. **Synthetic data.** 300 generated samples (90 test) with `clinical_validation: false`; N = 90 gives a Wilson CI of
    ≈ ±10 points and N = 20 resolves only large differences ([`data/trace2_data.npz`](../data/trace2_data.npz) metadata).
11. **Reconstructed corner and sizing.** `fitc10` is C10-DNTT on Si (not foil), currents read by eye, JOFF/LOV not
    fitted; the Variant 3 sizing is rebuilt from the author's decisions, one of them made after seeing data (D11).
12. **Assumed mismatch and proxy aging.** No measured mismatch or bias-stress data exist for this stack; flat σ (31–41 %)
    is a worst case, size-scaled V_th (57–64 %) the closest estimate, both with 5 dies per level
    ([phase3B.json](../results/fitc10_campaign/summary/v3/phase3B.json), [phase3B_V.json](../results/fitc10_campaign/summary/v3/phase3B_V.json)).
13. **Ideal host.** Noise-free I_DD meter and timer, ideal drivers, 1 mV level resolution. Design-time constants come
    from the same compact model they correct.
14. **Absolute times are model-dependent** (10–17 % in earlier work); trust ordering and gaps
    ([`docs/TOOLING.md`](TOOLING.md) §6).
15. **Not modelled:** layout parasitics, IR drop, noise, pad/ESD, host electronics energy.

---

## 7. File map for an implementer
| What | Where |
|---|---|
| Corner card | `rev10/sim/models/fitc10.lib` |
| Compact models | `rev10/sim/models/trace2_otft_v2.sub`, `trace2_otft_seg.sub` (+ `_mc` copies) |
| Base netlist | `rev10/sim/circuits/t5L_x2_v065.cir` |
| Frozen builder | `rev10/sim/tools/build_A.py` (+ `build_final.py`, `t11.py`, `t10.py`, `t8.py`, `t6fix.py`, `lockvar.py`) |
| Variant 3 resize | `results/fitc10_campaign/scripts/common.py::build(variant=3)` |
| v2 host stimuli, calibration, estimators | `results/host_v2/scripts/hv2.py` |
| v2.1 modes, idle, calibration | `results/host_v21/scripts/hv21.py` |
| Weights | `rev10/eval/F_hw_m4_firstpass.npy` |
| Canonical netlist | `docs/rev10_1_nominal.cir` (`tools/gen_nominal_netlist.py`) |
| Warm state (v1 / netlist) | `results/fitc10_campaign/raw/v3/warmstart/fitc10_warm.{dat,cols}` |
| v2.1 calibration start states | `results/host_v21/raw/cal/<key>/calibration.json` (`start_state`) |
| Reproduction | [`REPRODUCE.md`](../REPRODUCE.md) |
