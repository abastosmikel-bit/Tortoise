# Naming: public names and internal identifiers

The project was developed under a working name and revision labels. The public release uses the names in the left
column. File names, directory names, JSON keys, netlist text and command-line arguments that the scripts read were
**not** renamed, so that every script, checker and recorded result keeps working unchanged; they still carry the
working names listed on the right. This table lets you trace an old name in a file name, figure label or JSON key.

## Project and design labels

| Public name (in prose) | Working name / identifier | Where the identifier still appears |
|---|---|---|
| **Tortoise** | TRACE-2, TRACE2, `trace2` | netlist title line `TRACE-2 FINAL (frozen)` (matched by the builders, so the canonical netlist stays byte-identical); model files `trace2_otft*.sub/.lib`; data files `data/trace2_data.npz`, `data/trace2_fingers_retrained.npy`; the dataset's internal `metadata_json` name; JSON keys such as `trace2` in `results/wrapup/summary/s4_mcu.json` |
| **Tortoise v1.0** | Revision 10.1 (Rev. 10.1) | `docs/rev10_1_nominal.cir` (canonical netlist; read by `tools/gen_nominal_netlist.py`, `results/wrapup/scripts/s4_mcu.py`, `s3_variant.py`) |
| **the base design** / **the current design** (lab corner, before the `fitc10` resize) | Revision 10 (Rev. 10) | directory `rev10/` (all builders, models and evaluation scripts; hard-coded through the `/home/claude/w` layout) |
| **an earlier design iteration** | Revision 9 and before | not included in this release; netlist header comments inherited from it ("Rev-4 Autonomous", "145-TFT budget", …) remain in the base netlists, see [`SPEC.md`](SPEC.md) §2.4 |
| `/home/claude/w/repo` (layout link to the clone) | `/home/claude/w/TRACE-2-main` | renamed in every script; not stored in any result file |
| `/home/user/TRACE-2/...` | absolute path of the working copy when the campaigns ran | recorded as provenance (`prior`, `warm_start`, `src`, corner `.lib` paths) inside per-run JSONs, summaries and run logs; left as recorded |

## Candidate circuit variants (wrap-up Study 2 and Study 3)

| Public name | Identifier (file names, JSON keys, `s2_runs.py` / `s3_runs.py` arguments) | What it is |
|---|---|---|
| **candidate-edgeA** | `R10.2-edgeA` | X80 (idle pull-down of `win`) L 120 → 20 µm; 134 TFTs |
| **candidate-edgeB** | `R10.2-edgeB` | P_k pull-ups X90/X100/X110/X120/X130 L 5 → 10 µm; 134 TFTs |
| **candidate-bias** | `R10.2-bias` (weights `S3_le60_m30_b138`) | per-class bias row; 138 TFTs |
| candidate-… (generic) | `R10.2-<name>` | any named variant of the wrap-up studies |

Examples: `results/wrapup/summary/s2_design_R10.2-edgeA.json` is the design record of candidate-edgeA; the key
`variants["R10.2-edgeA"]` in `s2_edge.json` holds its results; `summary/s2_tables.md` is generated from those keys and
therefore shows the identifiers.

## Campaigns and studies

The campaigns were run as separate work streams. In the public documents they are named by their content:

| Name in the documents | Folder | Notes |
|---|---|---|
| the `fitc10` campaign | [`results/fitc10_campaign`](../results/fitc10_campaign/REPORT.md) | corner, Variant 3, nominal accuracy, stress, corner and mismatch sweeps |
| the weight-retraining study | [`results/weights_schemeA`](../results/weights_schemeA/REPORT.md) | the surrogate parameter stage `retrain_study` in `results/wrapup/scripts/s3_train.py` and the key `retrain_study_nominal` in `s3_surrogate_params.json` refer to it |
| the energy/host study | [`results/energy_host`](../results/energy_host/REPORT.md) | labels such as "energy/host study E11.1" in `results/host_v2/summary/c6_lower_edge.json` refer to its decision items |
| the host-v2 study | [`results/host_v2`](../results/host_v2/REPORT.md) | host protocol v2 |
| the host-v2.1 study | [`results/host_v21`](../results/host_v21/REPORT.md) | host protocol v2.1 |
| the wrap-up studies (Studies 1–4) | [`results/wrapup`](../results/wrapup/REPORT.md) | rows `WU-…` of the results index |

## Other identifiers that look like names

- `TRACE` / `TRACE_US` / `trace=` in the builders and campaign scripts is the **race-window length** parameter (µs), not
  the project name.
- `raw/s2_stress_R10.2-edgeA/` and similar raw folders keep the variant identifiers.
- Commit hashes quoted in the campaign records (e.g. "frozen … commit `8948461`") refer to the private development
  history in which the protocols were time-stamped; that history is not part of this release.
- References to a campaign's "PROGRESS log" or "progress log item N" point to working logs that are not part of this
  release.
