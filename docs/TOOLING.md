# Tortoise: base design and simulation tooling

This document describes the **base design** that Tortoise v1.0 is built on (the circuit as frozen at the lab device
corner, before the `fitc10` resize), the simulation tools in [`rev10/`](../rev10/), and the practical pitfalls found
while using them. The v1.0 design itself (corner, Variant 3 resize, weights, host protocol v2.1) is specified in
[`SPEC.md`](SPEC.md); the reproduction steps are in [`REPRODUCE.md`](../REPRODUCE.md).

Everything here is simulation (ngspice-42). The directory name `rev10/` and several file names are internal
identifiers that the scripts read; see [`NAMING.md`](NAMING.md).

Contents: 1 scope · 2 base design · 3 lab-corner notes · 4 setup and smoke test · 5 tools and files · 6 gotchas ·
7 open items at the freeze

---

## 1. Scope

The base design is a 6-input × 5-class linear classifier built only from p-type DNTT OTFTs on AlOx/SAM
(C_i 0.70 µF/cm²), on a single 3.3 V rail, with a 3.5 V dielectric stress limit. Each class charges a rail capacitor;
the first rail to reach threshold latches and locks out the others. The builders in `rev10/sim/tools/` produce this
design at the lab corner; the campaigns in [`results/`](../results/) apply the `fitc10` corner and the Variant 3 resize
on top of it (`results/fitc10_campaign/scripts/common.py::build`).

---

## 2. Base design (what `rev10/sim/tools/build_A.py` produces): 134 TFT instances

- **Model.** `rev10/sim/models/trace2_otft_v2.sub` (charge-based capacitance). The crossbar uses
  `trace2_otft_seg.sub` (5-segment channel, captures transit delay). Lab corner: `vth_sweep.lib lab_vth085` (µ 1,
  C_i 0.70 µF/cm², SS 80 mV/dec, R_C·W 400 Ω·cm, L_ov 2 µm).
- **Weights.** `rev10/eval/F_hw_m4_firstpass.npy` (hardware-trained), 60 fingers per column. Crossbar W = 10 µm ×
  fingers, L = 54 µm; the 9 empty banks are removed.
- **Rails and resets.**
  - C_rail = 375 pF.
  - Reset switches M75–79 are **400/20**, sized for mismatch: each rail's reset level equals its switch's |V_th|,
    one-for-one.
- **Comparator (variant C).** M81 468/15, M82 20/20, M83 200/10.
- **Lock (V2).** P_k 80/5, C_win 0.3 pF, `nb` load M87 family 20/5 (this halves the lock latency), lock devices M89
  20/5 gated by `lockb`, `win` precharge XWR from `rstr`.
- **Latch reset** pulls `nb` up (M88 → `nb rstr vdd`).
- **Latch-history equaliser.** XNP1–5 (`na rstb vdd`, 20/5).
- **No negative voltages anywhere.** Gate-grounded loads; the on-chip sequencer (SEQ8) is removed.
- **Host timing and levels.** 4 timing lines (`rstr`, `rstb`, `phib`, `phi`) plus the row levels.

Design choices made at the freeze: no negative bias; host timing instead of the on-chip sequencer; hardware-trained
weights; scheme A ("integrate, then race").

### 2.1 Host protocol of the base design (µs)
| Line / phase | Timing |
|---|---|
| `rstr` | 3.3 → 0 over 0–20, then low until 311.5, back high by 312.5 |
| `rstb` | low 0–150 (latch precharge) |
| `phib` | low until 309, back high by 310 (sampling ends before rows return high) |
| `phi` | complement of `phib` |
| Rows during reset | inactive (3.3 V) 0–301 |
| Calibration | all rows at V₁, 302–310 |
| **C1 (integrate)** | from 312.5: row *i* at V₁ for 20 + x_i·T₁ (T₁ = 170), once; all rows off 5 µs |
| **C2 (race)** | all rows at V₂; first rail to threshold wins |

Row levels are **referenced to V_th**: V₁ = 3.3 − |V_th| − 0.83 (1.62 V at 0.85 V), V₂ = 3.3 − |V_th| − 0.25
(2.20 V at 0.85 V). Every row switches on and off once per inference, so the turn-on loss is common to all classes.
Host protocols v2 and v2.1 (power gating, learned |V_th| and µ) replace this for v1.0; see [`SPEC.md`](SPEC.md) §4.

---

## 3. Lab-corner notes (recorded when the base design was frozen)

These numbers come from the lab-corner work (|V_th| = 0.85 V) that preceded the campaigns. The repository has **no
summary files or per-run data** for them, so they are not indexed in [`RESULTS_INDEX.md`](../RESULTS_INDEX.md) and are
not used as headline results. [`DESIGN_LESSONS.md`](DESIGN_LESSONS.md) cites them as *(lab-corner notes)*.

### 3.1 Why the circuit was redesigned
An earlier design iteration was verified only with a Level-1 MOSFET placeholder card (no subthreshold conduction, no
contact resistance, one fixed V_th, and, because the card has no oxide thickness, essentially no gate capacitance).
With C_i = 0.70 µF/cm² the real gate capacitance is 30–300× larger. Re-simulated with the charge-based OTFT model, that
earlier netlist did not classify, and its bootstrapped negative rails (−1.3 to −2.9 V) put 17 devices above the 3.5 V
dielectric limit, up to 6.2 V. Bootstrap pumps, detect nodes and lock nets sized against the placeholder all had to be
redesigned; the base design above is that redesign.

### 3.2 Key results at the lab corner (|V_th| = 0.85 V, 90 test samples)
- **Accuracy**, with the analytic model calibrated and checked in SPICE:
  - hardware-trained weights in software: 70.0 % (the initial integer weights `data/trace2_fingers_retrained.npy`:
    76.67 %);
  - hardware, nominal: 66.7 %;
  - Monte Carlo mean: 59.6 % at a 50 mV anchor, 65.2 % at 20 mV; worst 5 % of dies: 51.1 % / 61.1 %;
  - mismatch anchor: σ_Vth = anchor·√(780 µm²/WL). No published Pelgrom value exists for this stack, so 20–50 mV is a
    bracket.
- **Model against SPICE.**
  - Race model vs SPICE: race time within ≈ 2 %, gap within ≈ 1 µs (#31: 12.7 vs 13.4 µs).
  - SPICE Monte Carlo on 3 dies (#81): model and SPICE agree on the winner 3/3 (classes 4, 4, 2).
  - Compact model vs its Python reference: 16/16 DC points within 0.005 % (0.95 % at one off-state point, explained by
    the leakage resistor).
  - Warm restarts: the reset clears the previous winner; rails equalise to ≈ 12 mV on a mismatched die.
  - Stress audit: 0 devices above 3.5 V (max 3.40 V). The crossbar was not in that audit and the audit was not re-run
    after the reset-switch resize; both were done later in the campaigns (`tools/audit.py`, fitc10 Phase 2).
- **|V_th| = 1.15 V corner: fails** (all classes trip during integration). Causes:
  1. window ≈ V_DD − 2|V_th| (0.31 V against 0.70 V `ref` − rail): fundamental;
  2. the `ref` reset is history-dependent: precharging `ref` from `rstb` fails because M69 shares `rstb`; it needs a
     separate host line;
  3. rails converge slowly (179 mV spread after 300 µs);
  4. the calibration dead time depends on V_th.
  - Model with ideal resets: 36.8–51.4 % at 1.15 V, 51.6–61.5 % at ≈ 1.0 V.
  - Requirement: end-of-life |V_th| ≲ 0.9–1.0 V, i.e. a low-V_th process.

### 3.3 Design rules found at the lab corner
1. **Placeholder models hide 30–300× gate capacitance** and invert conclusions.
2. **Resolution law** for rate-coded races: Δt = K(s₁ − s₂)/(s₁s₂), K ≈ 1.03e5 µs·µm (pulse scheme). In scheme A the
   voltage gap is linear in the score difference and Δt = ΔV / (C2 slope).
3. **Lock latency comes from the ratioed latch trip point** (regeneration only above V_DD − |V_th|), not from logic
   depth. Lowering the trip point (one load resized) halved it.
4. **No negative bias → usable window ≈ V_DD − 2|V_th|.**
5. **Gate-grounded reset floors inherit ΔV_th 1:1,** and **latches remember the previous winner.** Both are invisible
   in cold start: always simulate warm starts from real end states.
6. **µs pulse encoding is faster than a long-channel OTFT responds** (transit ≈ 35 µs at L = 54 µm): 23–41 % charge
   loss. Hence "integrate, then race".
7. **A p-type ratioed stage cannot drive 0 V lows** (≈ 0.9–1.5 V after 200 µs). Resets need host lines.

---

## 4. Setup and smoke test

1. `apt-get install -y ngspice` (ngspice-42 was used throughout) and `pip install numpy`.
2. The scripts hard-code the layout `/home/claude/w/...`. Recreate it with symlinks to a clone:
   `sh tools/setup_layout.sh` (details in [`REPRODUCE.md`](../REPRODUCE.md) §3).
3. Smoke test of the builder at the lab corner:
   ```sh
   cd /home/claude/w/sim/circuits && OUT=/tmp/t.cir python3 ../tools/build_A.py 81 t6L_v085
   ```
   It prints "C2 starts at 507.5 us" and writes a netlist with 134 `X` lines. The full smoke test, with five real
   transients compared against recorded outcomes, is `sh tools/smoke_test.sh` ([`REPRODUCE.md`](../REPRODUCE.md) §5).

---

## 5. Tools and files (`rev10/`)

- `sim/models/`
  - `trace2_otft_v2.sub`: main compact model (charge-based capacitance).
  - `trace2_otft_seg.sub`: segmented-channel crossbar model.
  - `trace2_otft_v2_mc.sub`, `trace2_otft_seg_mc.sub`: the same equations with per-instance `DVTH`, `KMU`, `KRC` for
    Monte Carlo.
  - `trace2_otft.lib`: lab and printed corners. `vth_sweep.lib`: `lab_vth070/085/100/115`.
  - `fitc10.lib`, `fitc10_sweep.lib`: the `fitc10` corner and its one-dimensional sweeps ([`SPEC.md`](SPEC.md) §1).
  - `trace2_otft.sub`: v1 model, legacy.
- `sim/tools/`
  - `build_A.py`: **frozen design builder**: `python3 ../tools/build_A.py <test_idx> <prior_tag> [die_seed]`; env
    `VTH=085|115`, `OUT=`. Built on `build_final.py` → `t11.py` → `t10.py` → `t8.py` → `t6fix.py`, plus `lockvar.py`.
    The netlist title line "TRACE-2 FINAL (frozen)" is matched by later builders; do not edit it.
  - `run_diag.py`: simulate (`RELAX=1` relaxed tolerances, `AUDIT=1` writes the raw file for the stress audit,
    `EXTRA_NODES="a b"`). Writes `tag.dat` and `tag.cols`.
  - `score.py`: winner, order, lock, validity (`score(tag, t_on=320e-6, expect=k, t_off=...)`).
  - `lockmeas.py`, `audit.py`: lock-chain timing and gate-stress audit.
- `sim/circuits/`
  - `t5L_x2_v085.cir`, `t5L_x2_v115.cir`: base netlists the builders start from; `t5L_x2_v065.cir` is the copy with
    the `.lib` line pointing at `fitc10`.
  - `t6L_*.dat/.cols`: prior end states for warm starts (trimmed to the last rows). v085: `t6L_v085` = class 1 won,
    `t6L_x2_v085` = class 5 won; likewise for v115.
  - `A3_s81.cir`, `A3_s31.cir`: scheme-A runs at the lab corner (before the reset resize).
  - `MCR10{1,2,3}_s81.cir` + `_dvth.json`: Monte Carlo dies.
  - `V115_s81.cir`: the failing 1.15 V run.
  - `otft_*check.cir`: model checks (`ngspice -b otft_model_check.cir`).
- `eval/`
  - `schemeA.py`: **accuracy model for scheme A** (softplus mismatch, reset term, 20 µs pedestal, 14 µs lock).
  - `mc_compare.py`: per-die prediction from the SPICE draws.
  - `hw_retrain.py`, `hw_eval.py`: retraining (old pulse law).
  - `hw_accuracy.py`, `staircase.py`: older pulse-scheme analyses.
  - `F_hw_m4_firstpass.npy`: the chosen weights.
  - These scripts read `data/trace2_data.npz` and the initial integer weights `data/trace2_fingers_retrained.npy`
    (the starting point of the hardware-aware retraining) through `/home/claude/w/repo/data/`.
- `art/gen_layout.py`: illustrative to-scale SVG layout generator (an earlier placement; not DRC-checked).

---

## 6. Gotchas

- **Warm start matters.** Cold-start results hid the reset-floor and latch-history biases.
- **`.ic` + UIC artefact:** single-device tests show a +7.8 mV start-up offset. Subtract a no-stimulus baseline.
- **Order of Monte Carlo operations:** DVTH is drawn in `build_final` *before* `build_A` resizes the reset switches.
  `build_A` rescales those five DVTH values by √(500/8000) and keeps the json in sync.
- **`/bin/sh`, not bash:** no `<(...)` process substitution in the shell drivers.
- **Solver tolerances:** the original netlist tolerances (ABSTOL 1e-15) cause timestep failures with the charge
  model. Use `RELAX=1` (checked not to change the Level-1 baseline). Every campaign used this `RELAX=1` set.
- **Absolute race time** from the analytic model can be off by ≈ 10–17 % on mismatched dies. Trust ordering and gaps,
  not absolute times.
- **Run time:** one SPICE run takes 60–160 s on one core; the campaign runners use a process pool and are resumable
  (they skip runs whose per-run JSON exists).

---

## 7. Open items at the freeze

As recorded when the base design was frozen; items 1–5 were taken up by the campaigns in [`results/`](../results/).

1. Fit the compact model to a published *measured* DNTT dataset, ideally a low-V_th one (→ `fitc10` campaign).
2. Larger SPICE Monte Carlo, compared against `eval/mc_compare.py` (→ fitc10 Phase 3, host v2 C4).
3. Retrain the weights for the scheme-A timing law; `eval/hw_retrain.py` targets the old pulse law
   (→ weight-retraining study: no improvement found).
4. Re-run the stress audit on the final build, including the reset resize and the crossbar (→ fitc10 Phase 2 and
   later audits).
5. Power and energy estimate (→ energy/host study).
6. Fix the high-|V_th| corner: a separate host line for the `ref` reset, a longer or larger rail reset, longer
   sampling; only after a process target is set.
7. Literature comparison against printed-ML baselines (→ wrap-up Study 4, [`PRIOR_ART.md`](../results/wrapup/prior_art/PRIOR_ART.md)).
