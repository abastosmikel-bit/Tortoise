#!/usr/bin/env python3
"""
Generate physiology-inspired SYNTHETIC wound-panel data for Tortoise.

Output:
    trace2_data.npz (or trace2_synthetic_development_v1.npz)

Arrays read by the classifier scripts:
    X_train : float64, shape (210, 6), values in [0, 1]
    y_train : int64,   shape (210,), labels 0...4
    X_test  : float64, shape (90, 6), values in [0, 1]
    y_test  : int64,   shape (90,), labels 0...4

Dataset:
    300 total samples, 60 per class.
    30 synthetic acquisition groups, 10 samples per group.
    Each group contains two samples from each class.
    Groups are split, not individual observations.

This is NOT clinical data.
Class distributions, noise levels, and correlations are engineering
assumptions, not estimates fitted to patient measurements.

The generator does not load or use the classifier's weight matrix.
It does not tune samples to achieve a target classification accuracy.

Dependencies:
    Python 3
    NumPy

Example:
    python generate_wound_data.py
    python generate_wound_data.py --output trace2_data.npz --seed 202609
"""

import argparse
import json
from pathlib import Path

import numpy as np


FEATURE_NAMES = [
    "pH",
    "uric_acid",
    "lactate",
    "temperature",
    "pyocyanin",
    "impedance",
]

CLASS_NAMES = [
    "normal_healing_scenario",
    "acute_inflammation_scenario",
    "bacterial_colonization_scenario",
    "biofilm_formation_scenario",
    "critical_sepsis_benchmark_scenario",
]

# Central locations on a normalized scale.
CENTERS = np.array([
    # pH   uric  lact  temp  pyo   impedance
    [0.30, 0.25, 0.22, 0.40, 0.08, 0.78],
    [0.45, 0.62, 0.45, 0.68, 0.10, 0.60],
    [0.62, 0.48, 0.45, 0.57, 0.50, 0.50],
    [0.68, 0.58, 0.60, 0.62, 0.70, 0.36],
    [0.65, 0.60, 0.80, 0.82, 0.45, 0.25],
], dtype=np.float64)

LOADINGS = np.array([
    [0.10, 0.35, 0.10,  0.05],   # pH
    [0.35, 0.05, 0.25,  0.00],   # uric acid
    [0.15, 0.10, 0.45,  0.00],   # lactate
    [0.40, 0.10, 0.10, -0.05],   # temperature
    [0.00, 0.40, 0.05,  0.00],   # pyocyanin
    [-0.10, -0.15, -0.35, -0.30],# impedance
], dtype=np.float64)

RESIDUAL_SD = np.array(
    [0.32, 0.42, 0.42, 0.28, 0.45, 0.35], dtype=np.float64
)

GROUP_SD = np.array(
    [0.10, 0.12, 0.12, 0.08, 0.12, 0.15], dtype=np.float64
)

SENSOR_SD = np.array(
    [0.015, 0.025, 0.025, 0.012, 0.020, 0.025], dtype=np.float64
)

P_PYO_PRODUCER = np.array(
    [0.08, 0.12, 0.55, 0.70, 0.40], dtype=np.float64
)


def logit(x):
    x = np.clip(np.asarray(x, dtype=np.float64), 1e-6, 1.0 - 1e-6)
    return np.log(x) - np.log1p(-x)


def sigmoid(z):
    z = np.clip(np.asarray(z, dtype=np.float64), -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-z))


def make_group_split(rng, group_id):
    """Split acquisition groups so no group appears in both partitions."""
    group_order = rng.permutation(30)
    train_groups = group_order[:21]
    test_groups = group_order[21:]

    train_idx = np.flatnonzero(np.isin(group_id, train_groups))
    test_idx = np.flatnonzero(np.isin(group_id, test_groups))

    rng.shuffle(train_idx)
    rng.shuffle(test_idx)

    return train_idx, test_idx, train_groups, test_groups


def generate(seed):
    rng = np.random.default_rng(seed)

    group_id = np.repeat(np.arange(30, dtype=np.int64), 10)
    y = np.tile(np.repeat(np.arange(5, dtype=np.int64), 2), 30)

    n = len(y)
    assert n == 300

    latent_factors = rng.standard_normal((n, 4))
    residual = rng.standard_normal((n, 6)) * RESIDUAL_SD

    group_offsets = rng.standard_normal((30, 6)) * GROUP_SD

    z = (
        logit(CENTERS[y])
        + latent_factors @ LOADINGS.T
        + residual
        + group_offsets[group_id]
    )

    biological_signal = sigmoid(z)

    producer_present = rng.random(n) < P_PYO_PRODUCER[y]
    baseline_pyo = rng.beta(1.5, 25.0, size=n)
    biological_signal[~producer_present, 4] = baseline_pyo[
        ~producer_present
    ]

    sensor_error = rng.standard_normal((n, 6)) * SENSOR_SD

    outlier_mask = rng.random((n, 6)) < 0.01
    sensor_error += (
        outlier_mask
        * rng.standard_normal((n, 6))
        * 0.06
    )

    unbounded_measurement = biological_signal + sensor_error
    clipped_mask = (
        (unbounded_measurement < 0.0)
        | (unbounded_measurement > 1.0)
    )

    X = np.clip(unbounded_measurement, 0.0, 1.0).astype(np.float64)

    train_idx, test_idx, train_groups, test_groups = make_group_split(
        rng, group_id
    )

    illustrative_pH = 5.5 + 3.5 * X[:, 0]
    illustrative_temperature_c = 28.0 + 12.0 * X[:, 3]

    metadata = {
        # The dataset name keeps the project's working name so that the output reproduces data/trace2_data.npz.
        "dataset_name": "TRACE-2 synthetic wound-panel development data",
        "version": "1.0",
        "seed": int(seed),
        "synthetic": True,
        "clinical_validation": False,
        "total_samples": 300,
        "train_samples": int(len(train_idx)),
        "test_samples": int(len(test_idx)),
        "samples_per_class": 60,
        "feature_order": FEATURE_NAMES,
        "class_order": CLASS_NAMES,
        "split": (
            "21 training acquisition groups and 9 test acquisition groups; "
            "no acquisition group shared between partitions"
        ),
        "group_interpretation": (
            "Synthetic acquisition batches, not patients, not longitudinal "
            "wound trajectories. Every batch contains two samples per class."
        ),
        "normalization": {
            "pH": "Illustrative mapping x=(pH-5.5)/3.5",
            "temperature": "Illustrative mapping x=(temperature_C-28)/12",
            "uric_acid": "Relative sensor amplitude; no concentration mapping",
            "lactate": "Relative sensor amplitude; no concentration mapping",
            "pyocyanin": "Relative sensor amplitude; no concentration mapping",
            "impedance": (
                "Relative sensor amplitude increasing with impedance; "
                "no frequency-specific impedance calibration"
            ),
        },
        "assumptions": {
            "centers": CENTERS.tolist(),
            "latent_factor_loadings": LOADINGS.tolist(),
            "residual_sd_logit": RESIDUAL_SD.tolist(),
            "group_sd_logit": GROUP_SD.tolist(),
            "sensor_sd_normalized": SENSOR_SD.tolist(),
            "pyocyanin_producer_probability": P_PYO_PRODUCER.tolist(),
            "measurement_outlier_probability_per_entry": 0.01,
            "measurement_outlier_sd_normalized": 0.06,
        },
        "limitations": [
            "No patient measurements or literature-fitted distributions.",
            "Balanced class allocation is not clinical prevalence.",
            "No guaranteed accuracy, separability, or time-race margin.",
            "No classifier weights are used to generate or reject samples.",
            "Class 4 is a benchmark scenario, not a validated sepsis diagnosis.",
            "No sensor chemistry, concentration, or impedance-spectrum validation.",
            "Group separation is not a substitute for patient-separated validation.",
        ],
    }

    arrays = {
        "X_train": X[train_idx],
        "y_train": y[train_idx],
        "X_test": X[test_idx],
        "y_test": y[test_idx],
        "X_all": X,
        "y_all": y,
        "group_id_all": group_id,
        "group_train": group_id[train_idx],
        "group_test": group_id[test_idx],
        "train_indices": train_idx,
        "test_indices": test_idx,
        "train_groups": train_groups,
        "test_groups": test_groups,
        "biological_signal_all": biological_signal,
        "pyocyanin_producer_present_all": producer_present,
        "measurement_clipped_all": clipped_mask,
        "illustrative_pH_all": illustrative_pH,
        "illustrative_temperature_c_all": illustrative_temperature_c,
        "feature_names": np.asarray(FEATURE_NAMES, dtype="U32"),
        "class_names": np.asarray(CLASS_NAMES, dtype="U48"),
        "metadata_json": np.asarray(
            json.dumps(metadata, indent=2, sort_keys=True)
        ),
    }

    validate(arrays)
    return arrays


def validate(arrays):
    Xtr = arrays["X_train"]
    Xte = arrays["X_test"]
    ytr = arrays["y_train"]
    yte = arrays["y_test"]

    assert Xtr.shape == (210, 6)
    assert Xte.shape == (90, 6)
    assert ytr.shape == (210,)
    assert yte.shape == (90,)

    assert np.all(np.isfinite(Xtr))
    assert np.all(np.isfinite(Xte))
    assert np.all((Xtr >= 0.0) & (Xtr <= 1.0))
    assert np.all((Xte >= 0.0) & (Xte <= 1.0))

    assert np.array_equal(np.bincount(ytr, minlength=5), [42] * 5)
    assert np.array_equal(np.bincount(yte, minlength=5), [18] * 5)

    train_groups = set(arrays["group_train"].tolist())
    test_groups = set(arrays["group_test"].tolist())
    assert train_groups.isdisjoint(test_groups)

    indices = np.concatenate([
        arrays["train_indices"], arrays["test_indices"]
    ])
    assert np.array_equal(np.sort(indices), np.arange(300))


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic wound-panel development data."
    )
    parser.add_argument("--output", default="trace2_data.npz")
    parser.add_argument("--seed", type=int, default=202609)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting an existing output file.",
    )
    args = parser.parse_args()

    output = Path(args.output)
    if output.suffix.lower() != ".npz":
        parser.error("--output must end in .npz")
    if output.exists() and not args.overwrite:
        parser.error(
            f"{output} already exists; use --overwrite to replace it."
        )

    output.parent.mkdir(parents=True, exist_ok=True)

    arrays = generate(args.seed)
    np.savez_compressed(output, **arrays)

    with np.load(output, allow_pickle=False) as loaded:
        assert loaded["X_train"].shape == (210, 6)
        assert loaded["X_test"].shape == (90, 6)
        json.loads(str(loaded["metadata_json"].item()))

    print(f"Saved: {output.resolve()}")
    print("SYNTHETIC DATA ONLY — not clinical validation.")
    print("Total samples: 300")
    print("Training: 210, with 42 samples per class")
    print("Test:      90, with 18 samples per class")
    print("Acquisition groups are disjoint across train/test.")
    print("No accuracy or margin target was used in generation.")
    print()
    print("Next command:")
    print("python3 rev10/eval/hw_retrain.py   (reads data/trace2_data.npz through the /home/claude/w layout)")


if __name__ == "__main__":
    main()
