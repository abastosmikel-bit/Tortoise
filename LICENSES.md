# Licences

Tortoise is published for open research use. **No patent has been filed or will be claimed on this design.**

Different parts of the repository are under different licences, because a circuit, a program and a report are
different kinds of work. Every file has exactly one licence; [`REUSE.toml`](REUSE.toml) records which, and
`reuse lint` ([REUSE](https://reuse.software/)) checks that every file is covered. The full licence texts are in
[`LICENSES/`](LICENSES/).

Copyright 2026 Mikel Lopez.

## Which licence covers what

| Licence | Covers | In plain words |
|---|---|---|
| [CERN-OHL-S-2.0](LICENSES/CERN-OHL-S-2.0.txt) (CERN Open Hardware Licence, strongly reciprocal) | **The hardware design:** all netlists (`*.cir`), compact-model and device-corner cards (`*.sub`, `*.lib`, including the corner files under `results/*/models/`), the Monte Carlo die files of the design netlists (`rev10/sim/circuits/*_dvth.json`), the specification [`docs/SPEC.md`](docs/SPEC.md) and the design/tooling description [`docs/TOOLING.md`](docs/TOOLING.md) | You may study, modify, simulate, fabricate and distribute the design and products made from it. If you distribute a modified design or products based on it, you must make the modified design source available under the same licence and keep the notices. |
| [Apache-2.0](LICENSES/Apache-2.0.txt) | **Code:** every script and program (`*.py`, `*.sh`): builders, simulation drivers, analysis, checkers and the dataset generator | You may use, modify and redistribute the code, also in closed products, if you keep the copyright and licence notices and mark your changes. It includes an explicit patent licence from contributors. |
| [CC-BY-4.0](LICENSES/CC-BY-4.0.txt) (Creative Commons Attribution 4.0) | **Everything else:** documentation and reports (`README.md`, `CONCEPT.md`, `RESULTS_INDEX.md`, `REPRODUCE.md`, `docs/DESIGN_LESSONS.md`, `docs/NAMING.md`, every campaign `REPORT.md` and `DECISIONS.md`), results (summaries, per-run JSON data, warm-start states `*.dat`/`*.cols`, audit outputs, run logs), weights (`*.npy`, `*.npz` and their records), the synthetic dataset `data/trace2_data.npz`, and metadata files | You may share and adapt the material for any purpose if you give appropriate credit (cite the work, see [`CITATION.cff`](CITATION.cff)), link to the licence and say what you changed. |

If you are unsure which licence applies to a file, `reuse spdx` prints the licence of every file.

## Not covered

- The prior-art notes ([`results/wrapup/prior_art/PRIOR_ART.md`](results/wrapup/prior_art/PRIOR_ART.md)) cite published
  works and datasheets by DOI or document number; those works are not included and remain under their own terms.
  The request log `results/wrapup/prior_art/lookups/LOG.jsonl` records only URLs, dates and checksums.
- No trademark rights are granted by any of these licences.
