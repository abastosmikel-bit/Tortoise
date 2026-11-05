# Design lessons from Tortoise

These are the findings most likely to transfer to other unipolar (p-type only) organic or printed time-domain
classifiers. Each lesson gives the evidence (numbers linked to the summary file they come from) and the scope in which
it was observed. **All evidence is from ngspice simulation** of a compact OTFT model at a reconstructed device corner
(`fitc10`, C10-DNTT on Si) or at the earlier lab corner, on a synthetic dataset; nothing was measured. A lesson is
only as general as its scope line says. Numbers marked *(lab-corner notes)* come from the notes recorded when the base design was frozen at the lab corner
([`TOOLING.md`](TOOLING.md) §3) and have no machine-readable summary in this repository.

---

### 1. A placeholder transistor model can hide most of the gate capacitance and invert design conclusions
An earlier design iteration was checked only with a Level-1 MOSFET card that has no subthreshold conduction, no contact resistance, one
fixed V_th, and no oxide thickness, hence essentially no gate capacitance. With C_i = 0.70 µF/cm² the real gate
capacitance is 30–300× larger *(lab-corner notes)*. Under a charge-based OTFT model that earlier netlist did not classify,
and its bootstrapped negative rails put 17 devices above the 3.5 V dielectric limit, up to 6.2 V *(lab-corner notes)*. Bootstrap pumps, detect nodes and lock nets sized against the
placeholder all had to be redesigned.
**Scope:** any circuit whose timing or charge budget depends on gate capacitance, at high-C_i (thin AlOx/SAM)
dielectrics. **Check before relying on a design checked only in simulation:** does the model card have a gate capacitance comparable to
C_i·W·L?

### 2. Without negative bias, the usable voltage window is ≈ V_DD − 2|V_th|
With gate-grounded p-type devices only, the rail cannot be reset below one |V_th| above ground and the comparator
reference cannot rise above one |V_th| below V_DD, so the window between rail reset level and threshold shrinks as
|V_th| grows. At the `fitc10` corner with the host levels re-trimmed to each |V_th|, `ref` − rail reset falls from
0.477 V at 0.65 V to 0.441 / 0.404 / 0.365 / 0.323 V at 0.75 / 0.85 / 0.95 / 1.05 V, and strong samples start to trip
during integration (0, 0, 2, 9 of 20 runs at 0.75–1.05 V)
([phase3A_T.json](../results/fitc10_campaign/summary/v3/phase3A_T.json)). The climb the leading rail must make in the
race phase falls from 0.55 V at 0.65 V to 0.29 V at 0.85 V and 0.10 V at 1.00 V
([b4_mu_explain.json](../results/energy_host/summary/b4_mu_explain.json)). At the lab corner the design failed outright
at |V_th| = 1.15 V *(lab-corner notes)*.
**Scope:** single-rail unipolar designs with no negative supply and gate-grounded resets. **Rule of thumb:** keep
end-of-life |V_th| well below V_DD/2; here classification degraded from ≈ 0.95 V upward at V_DD = 3.3 V.

### 3. Re-trimming the host levels to |V_th| is mandatory, and the host can learn |V_th| itself
The race-phase overdrive is 3.3 − V₂ − |V_th|. With levels fixed at their 0.65 V values it is 0.25 V at nominal and
0.05 V at 0.85 V, and the race slope collapses from 0.63 to 0.09 mV/µs
([phase3A_c2slope.json](../results/fitc10_campaign/summary/v3/phase3A_c2slope.json)). Fixed levels therefore give
0/20 at every |V_th| ≥ 0.85 V ([phase3A.json](../results/fitc10_campaign/summary/v3/phase3A.json)) and 0/20 at an aging
proxy of +0.20 V for every mobility ([b4_aging.json](../results/energy_host/summary/b4_aging.json)), while levels
re-trimmed by V₁ = 3.3 − |V_th| − 0.83 V, V₂ = 3.3 − |V_th| − 0.25 V give 14/20 at 0.85 V
([phase3A_T.json](../results/fitc10_campaign/summary/v3/phase3A_T.json)). The host can estimate |V_th| from its own
supply current (a1 method): over a 25-cell aging grid its error was −4.4 … +8.5 mV and every cell classified at
13–15/20 ([c3_aging.json](../results/host_v2/summary/c3_aging.json)), inside the level tolerance measured by 1D sweeps
(V₂ −25 … +75 mV at 0.65 V; [b2_retrim.json](../results/energy_host/summary/b2_retrim.json)).
**Scope:** threshold-referenced level schemes in which a host drives the analog row levels. The tolerance band comes
from 20-sample sweeps and the combined shift of both levels was not simulated.

### 4. Accuracy is limited by the architecture, not by the weights
The crossbar has no per-class bias and all columns have the same finger budget. In nested cross-validation on the
training data a general float linear classifier reaches 73.7 %, the crossbar's own form (no bias, equal column sums)
67.9 %, and integer fingers 68.1 % ([A0_ceilings.json](../results/weights_schemeA/summary/A0_ceilings.json)).
Retraining the weights for the scheme-A timing law gave the same test accuracy, 62/90, with 6 samples gained and 6 lost
(McNemar p = 1.0) and lower validity, 82/90 against 87/90
([A2_FINAL_frozen.json](../results/weights_schemeA/summary/A2_FINAL_frozen.json)). The SPICE accuracy of the nominal
die (68.9 %) already sits next to the weights' software accuracy (70.0 %)
([phase1.json](../results/fitc10_campaign/summary/v3/phase1.json)).
**Scope:** winner-take-all races with equal per-class pedestals. **Lever:** a per-class bias (an extra host-driven
"bias row", or host-set per-class rail reset levels) is worth ≈ 6 points in the CV ceilings; it was not simulated.

### 5. Gate-grounded reset floors and comparator senses turn device mismatch into per-class offsets; size them
Each rail resets to its reset switch's |V_th|, one-for-one (+0.999 per volt), and the comparator sense device shifts the
trip level by −1.014 per volt ([surrogate_params.json](../results/weights_schemeA/summary/surrogate_params.json)). With
the same V_th spread on every device regardless of size, the median die sent 61 % of its valid answers to one class and
accuracy fell to 39/100; with σ_Vth scaled by √(780 µm²/WL), which shrinks it on the large reset (400/20 µm) and sense
(468/15 µm) devices, the same random numbers gave 64/100 and a 32 % dominant-class share
([phase3B_V.json](../results/fitc10_campaign/summary/v3/phase3B_V.json), `pairs`;
[phase3B.json](../results/fitc10_campaign/summary/v3/phase3B.json)).
**Scope:** any rate- or time-race classifier whose per-class start or threshold level comes from a single device.
Both mismatch models are assumptions; no measured Pelgrom coefficient exists for this stack.

### 6. In "integrate, then race", the race is very linear: the decision is the integration-phase voltage gap divided by the race slope
A physical race model fitted on 40 training runs reproduces the integration-phase rail charge to 0.13 mV rms and agreed
with SPICE on 40/40 winners for 40 held-out samples, with gap correlation r = 0.9998
([A0_calibration.json](../results/weights_schemeA/summary/A0_calibration.json)). Against the 90 test runs the older
lab-calibrated model had r = 0.9999 for the runner-up gap ([phase1.json](../results/fitc10_campaign/summary/v3/phase1.json)).
For rate-coded pulse races the corresponding law is Δt = K(s₁ − s₂)/(s₁s₂) *(lab-corner notes)*.
**Scope:** linear integration with a common ramp; absolute race times are model-dependent (10–17 %, *lab-corner notes*), so
use such models for ordering and gaps, not for absolute timing.

### 7. Near ties are decided by latch regeneration, not by lock latency
At nominal, 4 runs stayed valid with a runner-up gap below the lock latency (19.2 µs median); the failures are double
latches with gaps of a few µs, and the fitted resolve threshold is G_res = 8.70 µs
([phase1.json](../results/fitc10_campaign/summary/v3/phase1.json); [A0_calibration.json](../results/weights_schemeA/summary/A0_calibration.json)).
The binding limit is the slow regeneration of the ratioed latch (`na` takes ≈ 25 µs from 1.4 to 3.1 V;
[fitc10 REPORT §3.2](../results/fitc10_campaign/REPORT.md)). Near-tie double latches are the dominant failure under
size-scaled mismatch and across the aging grid ([phase3B_V.json](../results/fitc10_campaign/summary/v3/phase3B_V.json),
[c3_aging.json](../results/host_v2/summary/c3_aging.json)). At the lab corner, lowering the ratioed latch's trip point
halved the lock latency *(lab-corner notes)*.
**Scope:** ratioed p-type latches with long-channel loads. A host can also report a double latch as "no decision"
(not simulated).

### 8. Simulate warm starts and chains, not only cold starts
Latches remember the previous winner and rails carry the previous end state unless something erases it; both were
invisible in cold-start simulation *(lab-corner notes)*. With VDD left on between classifications, chained runs shifted the
first trip by up to 4.1 µs ([chain.json](../results/fitc10_campaign/summary/v3/chain.json)); with VDD switched off for
1 s, by 0.003 µs ([c1_nominal.json](../results/host_v2/summary/c1_nominal.json)); in the VDD-on mode W at 0.51 V the
race moved by up to 19 µs and one near-tie outcome changed out of 20
([e1_lower_edge.json](../results/host_v21/summary/e1_lower_edge.json)). The start state also moved the low-|V_th| edge
(lesson 10).
**Scope:** any circuit with gate-grounded resets or latches; a history-induced shift of a few µs is comparable to the
≈ 9 µs near-tie threshold.

### 9. Mobility loss is a timing problem that the host can fix by stretching time
Halving µ halves both the integration charge and the race slope, so class separation in time is preserved but races
outrun a fixed window: 8/20 with 6 timeouts at µ ×0.5 under fixed timing
([b4_aging.json](../results/energy_host/summary/b4_aging.json)). Scaling integration time and window by 1/µ (ideal
knowledge) gave 15/20 ([c3_aging.json](../results/host_v2/summary/c3_aging.json), `v1_E11_2_T1x2`); scaling by the
host's own µ estimate gave 15/20 at every µ from ×1 to ×0.5 at nominal |V_th|
([c3_aging.json](../results/host_v2/summary/c3_aging.json)).
**Scope:** global (die-wide) mobility loss; aging inputs are literature proxies with no per-device drift.

### 10. Unipolar ratioed logic has a low-|V_th| edge, and it moves with the start state
A p-type "off" device whose gate cannot reach VDD is not fully off at low |V_th|. Here the trip driver's gate sits at
the level-shifted reference (≈ 2.7–2.9 V), so at low |V_th| it holds every latch high: stuck latches at |V_th| ≤ 0.541 V
with warm starts ([b5_short_fixed.json](../results/energy_host/summary/b5_short_fixed.json)). Releasing the latch
precharge earlier moved the edge to 0.477 V ([b5_short_rstb50.json](../results/energy_host/summary/b5_short_rstb50.json)),
but power gating removed the residual reference charge this relied on and moved the edge up to 0.57–0.59 V
([c6_lower_edge.json](../results/host_v2/summary/c6_lower_edge.json)); keeping VDD on for low-|V_th| dies brought it
back to between 0.49 and 0.51 V ([e1_lower_edge.json](../results/host_v21/summary/e1_lower_edge.json)). A p-type ratioed
stage also cannot drive a clean 0 V low (≈ 0.9–1.5 V after 200 µs), so resets need host lines *(lab-corner notes)*.
**Scope:** ratioed unipolar logic with gate-grounded loads; the circuit-side fixes (drive the comparator output to VDD
when idle, a stronger latch reset) were proposed, not simulated.

### 11. Static current, not switching, sets the energy; gating time is the lever
99.97 % of the 714 nJ per classification comes from VDD, and the level-shift bias (358 nJ) and ratioed latch loads
(192 nJ) dominate; the crossbar takes 85 nJ ([b1_energy.json](../results/energy_host/summary/b1_energy.json)). Left
powered, the die idles at 98–199 µW, so at one classification per second idle costs ≈ 198 µJ against 0.68 µJ with VDD
switched off between classifications ([b1_energy.json](../results/energy_host/summary/b1_energy.json)); under host
protocol v2 a classification costs 588 nJ with zero standby ([c1_nominal.json](../results/host_v2/summary/c1_nominal.json)).
**Scope:** ratioed unipolar logic and source-follower biasing; no layout parasitics, pads or host electronics were
counted.

### 12. Power gating has electrical side effects: audit them
Switching VDD off drives internal latch nodes to ≈ −2.2 V, the next power-up starts from ≈ −2.04 V, and the crossbar's
stress margin falls from 1.07 V to 0.47 V ([phase2_audit.json](../results/fitc10_campaign/summary/v3/phase2_audit.json), [c2_stress.json](../results/host_v2/summary/c2_stress.json)). Ramps from
1 to 100 µs all stayed below the 3.5 V limit but none removed the negative nodes; the fastest (1 µs) left 64 mV of
margin through `win` overshoot ([e2_ramp.json](../results/host_v21/summary/e2_ramp.json)). Gating also moved the
low-|V_th| edge (lesson 10).
**Scope:** gated unipolar circuits with floating latch nodes; supply sequencing was not tried.

### 13. State the mismatch model: it decides the mismatch result
The same circuit gives 31–41 % under a flat σ_Vth with σ_µ and σ_RC on every device
([phase3B.json](../results/fitc10_campaign/summary/v3/phase3B.json)), 57–64 % with V_th scaled by device area
([phase3B_V.json](../results/fitc10_campaign/summary/v3/phase3B_V.json)), and 4–21 % if µ and R_C are also (wrongly)
area-scaled ([phase3B_P.json](../results/fitc10_campaign/summary/v3/phase3B_P.json)).
**Scope:** every mismatch claim for an emerging-device process without measured matching data; report the model next
to the number.

### 14. µs-scale pulse encoding is faster than a long-channel OTFT responds
With transit ≈ L²/(µ·V_ov) ≈ 35 µs at L = 54 µm (lab corner), pulse-width encoding lost 23–41 % of the charge in
simulation; one integration window per row, followed by a common race ramp ("integrate, then race"), avoids it
*(lab-corner notes)*.
**Scope:** OTFT channel lengths of tens of µm at mobilities of a few cm²/Vs.

---

**Methodology notes that helped** (from the campaigns' DECISIONS records and run logs): fixing each protocol and its pass
criteria in writing before the runs, labelling post-hoc decisions as such (e.g. fitc10 D11), recomputing every summary
from per-run files by script, and an independent audit of the weight-selection pipeline, which found one undeclared
optimiser start ([weights_schemeA REPORT §7](../results/weights_schemeA/REPORT.md)).
