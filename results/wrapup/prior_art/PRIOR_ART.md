# Study 4: prior art and the microcontroller question

Protocol: [DECISIONS S4](../DECISIONS.md). Every work below was confirmed through a logged Crossref, Semantic Scholar
or arXiv lookup (one line per request, with the SHA-256 of the saved response, in
[`lookups/LOG.jsonl`](lookups/LOG.jsonl); the saved responses are third-party records, pages and datasheets and are not
redistributed in this release: `lookup.py` re-fetches them) and is cited with its DOI. **What a work "does" is taken only from its
abstract** (Semantic Scholar or Crossref response, or an abstract retrieved from a fetched page: nature.com or the
OpenAlex API, both logged); nothing was read beyond the abstracts, so numbers a paper reports only in its body are not
quoted. "—" means the abstract does not report it. This is a targeted search (about 40 queries), **not a systematic
review**.

## 1. Closest published work

### 1.1 Printed / flexible machine-learning classifiers
| Work | What it does (abstract) | Technology | Size / accuracy / energy in the abstract | How Tortoise differs |
|---|---|---|---|---|
| Mubarik et al., MICRO 2020, *Printed Machine Learning Classifiers*, DOI 10.1109/micro50266.2020.00019 | Hardware cost of MLP, SVM, LR, random-forest and decision-tree inference in printed technologies; bespoke, lookup-based and **analog printed classifiers**; SPICE/gate-level simulation and working prototypes | EGT and CNT-TFT printed | analog trees/SVMs 437×/490× less area than digital bespoke; "self-powered printed classifiers" feasible | Their analog classifiers are the closest functional analogue; Tortoise uses a time race of integrated currents (not voltage-domain analog), one p-type OTFT, and is simulation only |
| Weller et al., Sci. Rep. 2021, DOI 10.1038/s41598-021-88396-0 | Inkjet-printed neuromorphic building blocks: inverter-based weight representation, resistive crossbars, printed activation functions, and a training algorithm for the printed architecture | inkjet-printed | — | Same goal (classification in printed/flexible tech with hardware-aware training); Tortoise has no resistors, no activation function and decides by first arrival in time |
| Zhao et al., ICCAD 2022, *Aging-Aware Training for Printed Neuromorphic Circuits*, DOI 10.1145/3508352.3549411 | Stochastic aging model of printed resistors; training on the expected loss over lifetime | printed neuromorphic | 35.8 % better expected accuracy over lifetime | Tortoise handles drift by host re-calibration (learned \|V_th\|, µ) instead of aging-aware weights; aging here is a global proxy shift, not a measured model |
| Armeniakos et al., DATE 2022, DOI 10.23919/date54114.2022.9774689; IEEE TC 2023, DOI 10.1109/tc.2023.3251863 | Approximate-computing co-design of bespoke printed MLP/SVM circuits | printed electronics (digital bespoke) | 47 % / 44 % area / power reduction, < 1 % accuracy loss (DATE); 6× / 5.7× (TC) | Digital bespoke arithmetic; Tortoise avoids digital arithmetic altogether |
| Armeniakos et al., DATE 2024, *On-Sensor Printed ML Classification via Bespoke ADC and Decision Tree Co-Design*, DOI 10.23919/date58400.2024.10546585 | Bespoke ADCs co-designed with decision trees; the ADC named as the costly part of processing sensor inputs | printed | "self-powered operation" in all benchmark cases | Addresses exactly the ADC cost that Tortoise does **not** remove (Tortoise still needs digitised inputs from its host, §2) |
| Ozer et al., Nat. Electron. 2020, DOI 10.1038/s41928-020-0437-5 | Hardwired ML processing engine (univariate Bayes feature voting) for odour recognition | commercial 0.8 µm metal-oxide TFT, flexible | ≈ 1 000 logic gates | Fabricated and measured digital classifier on foil; Tortoise is an unfabricated analog-time design |
| Biggs et al., Nature 2021 (PlasticARM), DOI 10.1038/s41586-021-03625-w | A 32-bit Arm microprocessor on a flexible substrate | metal-oxide TFT | — | A general-purpose processor on foil exists; the "why not a processor" question applies on foil too |

### 1.2 Organic / OTFT neural and computing circuits on foil
| Work | What it does (abstract) | Technology | Size / energy in the abstract | How Tortoise differs |
|---|---|---|---|---|
| Myny et al., IEEE JSSC 2012, DOI 10.1109/jssc.2011.2170635 | 8-bit organic microprocessor on plastic foil running user programs | organic ("plastic") TFTs on foil, 10 V supply, 50 V back gate | 40 instructions/s, ≈ 100 µW | Digital, general purpose, measured; Tortoise is fixed-function analog-time, simulated |
| van de Burgt et al., Nat. Mater. 2017, DOI 10.1038/nmat4856 | Electrochemical organic synapse (ENODe) with > 500 non-volatile conductance states; classification in neural-network simulations; flexible version | organic electrochemical device | < 10 pJ switching for 10³ µm² devices | Programmable analog weights (Tortoise: fixed finger counts); classification only simulated there too |
| Harikesh et al., Nat. Electron. 2022, DOI 10.1038/s41928-022-00859-y | Organic artificial spiking neuron operating in liquid, sensitive to ion/dopamine concentration | organic electrochemical | — | Bio-interfacing neuron, not a classifier; points at sensing-to-time conversion that Tortoise does not have |

### 1.3 Time-domain, race-logic and temporal-coding computation
| Work | What it does (abstract) | Technology | Figures in the abstract | How Tortoise differs |
|---|---|---|---|---|
| Madhavan, Sherwood, Strukov, ISCA 2014, *Race Logic*, DOI 10.1109/isca.2014.6853226 | Information as a timing delay; computation by the outcome of races (min/max, addition by delay chaining) | 0.5 µm CMOS standard cells | up to 4× faster than a systolic array (DNA alignment) | **The race principle is not new.** Tortoise applies a single analog race (first rail to threshold) to a linear classifier |
| Tzimpragos et al., ASPLOS 2019, DOI 10.1145/3297858.3304036; CACM 2021, DOI 10.1145/3460223 | Race logic for in-sensor classification: boosted race trees | 14 nm CMOS (design) | 1 000 race trees, 15.2 M frames/s at 613 mW | Classification by races exists (trees, digital delays, CMOS); Tortoise is a linear classifier with analog integration, on OTFTs |
| Bavandpour, Mahmoodi, Strukov, IEEE TCAS-II 2019, DOI 10.1109/tcsii.2019.2891688 | Time-domain mixed-signal vector-by-matrix multiplier: time-encoded inputs, current-source weights | 55 nm with embedded NOR flash | ≈ 7 fJ/Op (post-layout estimate, N > 500) | Same input coding idea (time-encoded inputs × current weights, integrated on a capacitor); Tortoise ends in a winner-take-all race instead of time-encoded outputs |
| Ramakrishnan & Hasler, IEEE TVLSI 2014, DOI 10.1109/tvlsi.2013.2245351 | Vector-matrix multiply + winner-take-all as a programmable analog classifier; mismatch and temperature compensation discussed; measured | 0.35 µm CMOS chip | — | **VMM + WTA classification is not new**; Tortoise's WTA is a time race with a latch lock-out, in a unipolar OTFT process |
| Ramya, Maragathaeswari, Sadasivan, 5NANO 2021, DOI 10.1109/5nano51638.2021.9491130 | Simulation of a **thin-film-transistor winner-take-all circuit** (TFT SPICE parameters extracted from COMSOL device simulation), aimed at brightness tracking | polysilicon TFT (simulated) | ≈ 3.7 µs input-to-output delay | A TFT WTA has been simulated before; it is not a classifier and not organic/p-only; Tortoise's WTA is a race of integrated rails with a latch lock-out |
| Yamaguchi et al., IEEE Access 2021, DOI 10.1109/access.2020.3047619 | Time-domain analog neural-network computation with pulse-width-modulated signals: weighted sums by charging a capacitance | CMOS VLSI | — | Same "weighted sum by charging a capacitor with pulse widths" principle in CMOS; Tortoise's rail integration is this, followed by a race |
| Mostafa, IEEE TNNLS 2018, DOI 10.1109/tnnls.2017.2726060 | Training spiking networks with temporal (spike-time) coding; differentiable input–output relation | algorithm | MNIST | Time-to-first-spike readout is the same decision rule as Tortoise's first-rail-wins; Tortoise is one layer, trained with a race surrogate |

### 1.4 Unipolar (p-only) organic analog and mixed-signal circuits
| Work | What it does (abstract) | Technology | Figures in the abstract | How Tortoise differs |
|---|---|---|---|---|
| Marien et al., IEEE JSSC 2011, DOI 10.1109/jssc.2010.2073230 | Fully integrated first-order continuous-time ΔΣ ADC; V_t-insensitive amplifier, comparator, level shifter | pentacene dual-gate OTFT on foil | 26.5 dB at 500 Hz, 100 µA from 15 V, 13 × 20 mm² | Unipolar organic mixed-signal on foil is established (with a back gate); Tortoise is single-gate, 3.3 V, no ADC |
| Zaki et al., IEEE JSSC 2012, DOI 10.1109/jssc.2011.2170639 | 6-bit current-steering DAC with low-voltage organic **p-type** TFTs | stencil-mask OTFTs on glass, 3.3 V | 100 kS/s, 2.6 × 4.6 mm² | Same supply class (3.3 V, low-voltage p-type OTFTs); a converter, not a classifier |
| Huang et al., IEEE TED 2011, *Pseudo-CMOS*, DOI 10.1109/ted.2010.2088127 | Design style for monotype (p- or n-only) single-V_T TFTs with post-fabrication tunability | p-type SAM-organic and n-type IGZO TFTs | — | Tortoise uses ratioed logic and host-driven resets instead; pseudo-CMOS is the standard alternative for its latch/inverter (not tried here) |
| Kraft et al., Org. Electron. 2016, DOI 10.1016/j.orgel.2016.04.038 | Source of the `fitc10` corner (C10-DNTT on Si) per the repository record (`docs/SPEC.md` §1) | DNTT-family OTFTs | — (no abstract retrieved; no content claim made) | — |

### 1.5 Wearable / wound-sensing systems with processing
| Work | What it does (abstract) | Processing | How Tortoise differs |
|---|---|---|---|
| Shirzaei Sani et al., Sci. Adv. 2023, DOI 10.1126/sciadv.adf7388 | Stretchable wireless wound patch: multiplexed electrochemical biosensor array, combination therapy; preclinical in vivo | wireless electronics (abstract does not detail) | Tortoise's input panel (pH, uric acid, lactate, temperature, pyocyanin, impedance) is of this kind, but synthetic; Tortoise has no sensors |
| Mostafalu et al., Small 2018, DOI 10.1002/smll.201703509 | Flexible dressing with temperature and pH sensors and on-demand drug release | "equipped with a microcontroller" | The existing route: sensors on the dressing, a microcontroller decides |
| Pang et al., Adv. Sci. 2020, DOI 10.1002/advs.201902673 | Flexible electronics-integrated dressing: temperature sensor + UV LEDs + antibacterial hydrogel | — | Infection detection from wound temperature; the abstract describes no learned classifier |
| Kalasin et al., Anal. Chem. 2022, DOI 10.1021/acs.analchem.2c00782 | Chip-free bandage tag read contactlessly; deep ANN classifies healing stage | off-patch ANN | 94.6 % accuracy (their data); the patch has no processing at all, the opposite design choice |
| Wang, Shirzaei Sani, Gao, Adv. Funct. Mater. 2022, DOI 10.1002/adfm.202111022 | Review of wearable bioelectronics for chronic wounds, including closed-loop devices | review | Context only |

**Not found:** a search for organic or printed TFT circuits that classify by a time race or a winner-take-all
returned no matching classifier (the closest hits are the polysilicon-TFT WTA simulation and the CMOS PWM
network above) in the top Crossref and Semantic Scholar results
(log labels `*otft_wta*`, `*otft_timedomain*`, `*printed_timedomain*`, `*unipolar_comparator*` in `lookups/LOG.jsonl`). That is the absence of
a hit in a small search, not evidence that no such work exists.

## 2. Novelty statement
- **Not new:** computing with signal races and reading the first arrival (race logic, 2014; race-tree classifiers,
  2019); time-encoded inputs multiplied by current-source weights and integrated (time-domain VMM, 2019); VMM followed by
  winner-take-all as a linear classifier (measured in CMOS, 2014); weighted sums by charging a capacitor with
  pulse-width inputs (CMOS, 2021); a winner-take-all circuit in TFTs (polysilicon, simulated, 2021); classifiers built for printed and flexible
  technologies, including analog ones and hardware-aware training (2020–2024) and a measured flexible ML engine (2020);
  unipolar p-type organic analog/mixed-signal circuits at 3.3 V (2011–2012); wound dressings with sensors and a
  microcontroller (2018–2023).
- **Possibly new (not found in this search):** the specific combination — a linear classifier whose winner-take-all is
  an "integrate, then race" of rail voltages to a common threshold, in a single-gate p-type-only OTFT design at 3.3 V,
  with no negative supply, a latch lock-out, and a host that learns the die's |V_th| and µ from its own supply current
  and re-trims levels and timing.
- **Unclear:** whether the host-learned |V_th|/µ re-trim and the time-race readout have been combined before in
  printed/organic work (the search was not exhaustive), and whether any of this matters in hardware: nothing has been
  fabricated, and every result is a simulation of a reconstructed device model on synthetic data.

## 3. The microcontroller question
Arithmetic in [`../scripts/s4_mcu.py`](../scripts/s4_mcu.py) → [`../summary/s4_mcu.json`](../summary/s4_mcu.json).
Datasheets fetched and logged: TI MSP430FR2433 (SLASE59F) and TI MSPM0L1306 (SLASEX0D) (no DOI; vendor PDFs, logged
with SHA-256). Typical values at 25 °C. Workload: wake from sleep, 6 ADC conversions, 6 normalisations + 30 MACs + 5
biases + argmax (assumed 500 / 1 000 / 3 000 cycles; 3 000 = no hardware multiplier).

| | MSP430FR2433 (8 MHz, 3 V) | MSPM0L1306 (32 MHz, 3.3 V) | Tortoise (Tortoise v1.0, simulated) |
|---|---|---|---|
| Energy per classification | **0.42 µJ** (0.26–1.03 µJ over the cycle range): wake 0.02, 6 ADC 0.09, compute 0.31 µJ | **0.41 µJ** | **0.59 µJ on the die alone** (H2-02); the host is busy ≈ 2.2 ms per classification (median read time), which costs ≥ 1.1 µJ even idling in LPM0 at 1 MHz, plus the same 6 ADC conversions: **≥ 1.8 µJ at the system level** (excluding the V₁/V₂ drivers, the power switch and the I_DD meter) |
| Standby | 2.9 µW (LPM3), 0.05 µW (LPM4.5) | 3.3 µW (standby), 0.2 µW (shutdown) | 0 on the die (mode G); the host's own standby is the same as the left column |
| Accuracy on this task | any classifier the data support (a float linear classifier with bias: 73.7 % in training CV, WS-01) | same | 62/90 = 68.9 % (FC-01); bias-free form limits it (WS-02) |
| Size | 2.29 × 2.34 mm package (DSBGA-24), complete | 3 × 2 mm package (WQFN-16) | active area ≥ 1.89 mm² (TFT channels 0.30 mm² + rail/reference capacitors 1.59 mm² at 0.70 µF/cm²), without routing, contacts or pads; plus the host |
| Interconnect to the sensors' side | 6 analog inputs (+ reference) | same | 10 driven lines + 5 outputs + supply between host and foil, and the inputs still have to be digitised by the host |
| Calibration | none | none | ≈ 3.0 µJ per calibration session (H2-11) |

**Where Tortoise loses (plainly).** In the architecture simulated here the host must digitise the six sensor values
anyway (it turns each x_i into a pulse width), drive two analog levels on six rows with µs timing, meter its supply
current for calibration, and watch five outputs for ≈ 2.2 ms. An ultra-low-power MCU doing the same ADC conversions
can compute the 6 × 5 classifier itself in ≈ 0.1–0.4 ms for ≈ 0.3–1 µJ, with better accuracy (no bias-free constraint),
reprogrammable weights, no calibration, fewer interconnects and a measured, qualified part. Tortoise therefore **adds**
energy, interconnects and complexity to a system that already contains the MCU it would replace. Its die-only 0.59 µJ
is in the same range as the MCU's whole job, so it has no energy advantage either.

**Conditions under which a foil classifier could still make sense — arguments, not results** (none is simulated or
shown here):
1. **Sensor-to-time on the foil.** If each sensor drove its row directly (a sensor whose current or a pulse it shapes
   is the row input), no ADC and no host-generated pulses would be needed; the foil-to-host link could shrink to
   supply, a start line and a few output lines. This would remove the main reason Tortoise loses above. It needs a
   circuit (and sensors) that this project does not have.
2. **Disposable wound side, reusable host.** A dressing that is thrown away could carry only printed or organic parts
   (sensors, classifier), with the rigid MCU, battery and radio in a reusable clip outside the dressing; fewer, simpler
   contacts across the disposable/reusable boundary would then matter more than nJ.
3. **No rigid parts on the wound.** Conformal, thin and possibly transparent electronics on the wound side, with
   rigid parts kept away from it.
4. **Unit cost at volume, if printed.** Plausible for printed processes in general (the printed-ML literature above
   argues it), not established for this design or this OTFT process.

## 4. What this does not show
- Not a systematic review: about 40 queries; works outside them (including non-English, theses, patents) were not
  searched. A missing hit is not evidence of absence.
- Content claims rest on abstracts only; figures reported only in the papers' bodies, and their measurement
  conditions, were not read.
- The MCU numbers are datasheet typicals at 25 °C with an assumed cycle count; no MCU was programmed or measured. ADC
  input settling with high-impedance electrochemical sensors, the analog front-end the sensors need, the radio and
  battery are not counted, on either side.
- Tortoise's numbers are simulations (ngspice-42, reconstructed `fitc10` corner, synthetic data); its area is a channel +
  capacitor lower bound, not a layout; the host energy floor is an estimate from one MCU's LPM0 current.
