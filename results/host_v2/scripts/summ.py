"""Summaries for host protocol v2 (recomputed from the per-run JSONs). Usage: python3 summ.py [phase ...]
-> summary/<phase>.json (+ csv). v1 references are read from the earlier result folders (read-only)."""
import csv, glob, json, math, pathlib, sys
import numpy as np
import hv2

HV = hv2.HV
FC = hv2.REPO / "results/fitc10_campaign"
EHR = hv2.REPO / "results/energy_host"


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(c - h, 0.0), 4), round(min(c + h, 1.0), 4))


def mcnemar_exact(b, c):
    """Two-sided exact McNemar (binomial on the discordant pairs)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return round(min(1.0, 2 * p), 4)


def v2_correct(m):
    return bool(m.get("valid_read")) and m.get("winner_read") == m.get("label")


def v1_correct(m):
    return bool(m.get("valid")) and m.get("winner") == m.get("label")


def load(pattern):
    return [json.load(open(f)) for f in sorted(glob.glob(str(pattern))) if not f.endswith("_draws.json")]


def block(runs, v2=True):
    n = len(runs)
    corr = sum(v2_correct(m) if v2 else v1_correct(m) for m in runs)
    val = sum(bool(m.get("valid_read" if v2 else "valid")) for m in runs)
    fails = {}
    for m in runs:
        f = m.get("failure_read") if v2 else m.get("failure")
        if not v2 and f == "timeout" and m.get("latched"):   # fitc10 summarize.py::failure labelling
            f = "stuck_latched"
        if not v2 and f == "multi_latched" and m.get("lock_us") and any(
                m["trip_us"].get(str(k), m["trip_us"].get(k, 0)) > m["lock_us"] for k in m["latched"]):
            f = "lockout_failed"
        if f:
            fails[f] = fails.get(f, 0) + 1
    tc1 = sum(bool(m.get("trip_in_C1")) for m in runs)
    strict = sum((v2_correct(m) if v2 else v1_correct(m)) and not m.get("trip_in_C1") for m in runs)
    races = [m["race_us"] for m in runs if m.get("race_us") is not None]
    lat = [m["lock_latency_us"] for m in runs if m.get("lock_latency_us")]
    return dict(n=n, correct=corr, accuracy_wilson95=wilson(corr, n), valid=val, validity_wilson95=wilson(val, n), failures=fails,
                trips_in_C1=tc1, strict_correct=strict,
                race_us_median=round(float(np.median(races)), 1) if races else None,
                race_us_range=[round(min(races), 1), round(max(races), 1)] if races else None,
                lock_latency_us_median=round(float(np.median(lat)), 2) if lat else None)


def paired(a, b, fa=v2_correct, fb=v1_correct):
    """a, b: dict idx -> run. Returns counts and exact McNemar on correct/incorrect."""
    ks = sorted(set(a) & set(b))
    A = [fa(a[k]) for k in ks]; B = [fb(b[k]) for k in ks]
    bb = sum(x and not y for x, y in zip(A, B)); cc = sum(y and not x for x, y in zip(A, B))
    return dict(n=len(ks), both=sum(x and y for x, y in zip(A, B)), only_first=bb, only_second=cc, neither=sum(not x and not y for x, y in zip(A, B)),
                mcnemar_p=mcnemar_exact(bb, cc))


def outcome_v2(m):
    return m.get("winner_read") if m.get("valid_read") else (m.get("failure_read") or "no_data")


def outcome_v1(m):
    return m.get("winner") if m.get("valid") else (m.get("failure") or "no_data")
