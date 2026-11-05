"""A3 (DECISIONS.md W11): robustness of a frozen weight set on the campaign's 20-sample test subset, paired with the
old weights' campaign results on the same samples/corners/dies.
Usage: python3 robustness.py run <FINAL_name> <A|T|V ...> [nproc]    A: fixed-level |V_th| and mu sweep (3A),
                                                                    T: re-trimmed |V_th| sweep (3A-T),
                                                                    V: size-scaled V_th-only mismatch (3B-V), paired draws
       python3 robustness.py summary <FINAL_name>                   -> summary/A3_<FINAL_name>.json
Settings follow the campaign's phase3.py exactly (corners fitc10_sweep.lib, 2500 us window, the nominal warm start of the
weight set for every point, seeds 1000*anchor + die). The nominal point is the A2 run of the same sample."""
import json, sys
import numpy as np
import wcommon as W
import runs as R
from eval_test import frozen, outcome

CAMP_P3 = W.CAMP / "scripts"
sys.path.insert(0, str(CAMP_P3))
import phase3 as P3                      # noqa: E402  (A_POINTS, T_POINTS, V_ANCHOR_MV, B_DIES, SUB)

SUB = P3.SUB


def jobs(name, which):
    F, fro = frozen(name)
    prior = W.pathlib.Path(fro["warm_start"])
    base = dict(split="test", F=F, weights_name=name, prior=prior, timing=fro.get("timing"))
    out = []
    if "A" in which:
        out += [dict(base, tag=f"A_{p}_s{i:02d}", idx=i, outdir=W.RAW / f"A3_{name}/phase3A", wdir=f"wsA_3A_{name}", vth=vt,
                     corner=("fitc10_sweep.lib", f"fc10_{p}")) for p, vt in P3.A_POINTS for i in SUB]
    if "T" in which:
        out += [dict(base, tag=f"AT_{p}_s{i:02d}", idx=i, outdir=W.RAW / f"A3_{name}/phase3A_T", wdir=f"wsA_3AT_{name}", vth=vt,
                     levels_vth=vt, corner=("fitc10_sweep.lib", f"fc10_{p}")) for p, vt in P3.T_POINTS for i in SUB]
    if "V" in which:
        out += [dict(base, tag=f"V_an{a:02d}_d{d}_s{i:02d}", idx=i, outdir=W.RAW / f"A3_{name}/phase3B_V", wdir=f"wsA_3BV_{name}",
                     mc=dict(seed=1000 * a + d, s_vth=a / 1000, paired=True)) for a in P3.V_ANCHOR_MV for d in P3.B_DIES for i in SUB]
    return out


def failure(m):
    sys.path.insert(0, str(CAMP_P3))
    import summarize as CS
    return CS.failure(m)


def block(rs):
    n = len(rs); k = sum(1 for m in rs if outcome(m) == m["label"]); nv = sum(1 for m in rs if m.get("valid"))
    fails = {}
    for m in rs:
        if not m.get("valid"):
            f = failure(m); fails[f] = fails.get(f, 0) + 1
    ks = sum(1 for m in rs if outcome(m) == m["label"] and not m.get("trip_in_C1"))
    race = [min(m["trip_us"].values()) - m["tC2_us"] for m in rs if m.get("trip_us")]
    return dict(n=n, correct=k, accuracy=round(k / n, 4) if n else None, wilson95=W.wilson(k, n), valid=nv, failures=fails,
                strict_correct=ks, strict_wilson95=W.wilson(ks, n), n_trip_in_C1=sum(1 for m in rs if m.get("trip_in_C1")),
                race_from_C2_median_us=round(float(np.median(race)), 1) if race else None,
                lock_latency_median_us=round(float(np.median([m["lock_latency_us"] for m in rs if m.get("valid") and m.get("lock_latency_us")])), 2)
                if any(m.get("valid") for m in rs) else None)


def paired(new, old):
    keys = sorted(set(new) & set(old))
    a = {k: outcome(new[k]) == new[k]["label"] for k in keys}; b = {k: outcome(old[k]) == old[k]["label"] for k in keys}
    from eval_test import mcnemar_exact
    no, oo = sum(a[k] and not b[k] for k in keys), sum(b[k] and not a[k] for k in keys)
    return dict(n=len(keys), new_correct=sum(a.values()), old_correct=sum(b.values()), new_only=no, old_only=oo,
                same_outcome=sum(outcome(new[k]) == outcome(old[k]) for k in keys), mcnemar_exact_p=round(mcnemar_exact(no, oo), 6))


def load_dir(path):
    out = {}
    for f in sorted(path.glob("*.json")):
        if not f.name.endswith("_draws.json"):
            m = json.loads(f.read_text()); out[m["tag"]] = m
    return out


def summary(name):
    base = W.RAW / f"A3_{name}"
    nom = {m["idx"]: m for m in W.load_runs(f"test_{name}") if m["idx"] in SUB}
    old_nom = {i: json.loads((W.CAMP / f"raw/v3/phase1/s{i:02d}.json").read_text()) for i in SUB}
    res = dict(weights=name, subset=SUB, nominal=dict(new=block(list(nom.values())), old=block(list(old_nom.values())),
                                                      paired=paired({i: nom[i] for i in nom}, old_nom)))
    A = load_dir(base / "phase3A"); oA = load_dir(W.CAMP / "raw/v3/phase3A")
    res["3A_fixed_levels"] = {}
    for p, vt in P3.A_POINTS:
        n_ = {k: v for k, v in A.items() if k.startswith(f"A_{p}_")}; o_ = {k: v for k, v in oA.items() if k.startswith(f"A_{p}_")}
        if n_:
            res["3A_fixed_levels"][p] = dict(new=block(list(n_.values())), old=block(list(o_.values())), paired=paired(n_, o_))
    T = load_dir(base / "phase3A_T"); oT = load_dir(W.CAMP / "raw/v3/phase3A_T")
    res["3A_T_retrimmed"] = {}
    for p, vt in P3.T_POINTS:
        n_ = {k: v for k, v in T.items() if k.startswith(f"AT_{p}_")}; o_ = {k: v for k, v in oT.items() if k.startswith(f"AT_{p}_")}
        if n_:
            res["3A_T_retrimmed"][p] = dict(levels=dict(V1=round(3.3 - vt - 0.83, 3), V2=round(3.3 - vt - 0.25, 3)),
                                            new=block(list(n_.values())), old=block(list(o_.values())), paired=paired(n_, o_))
    V = load_dir(base / "phase3B_V"); oV = load_dir(W.CAMP / "raw/v3/phase3B_V")
    res["3B_V"] = {}
    for a in P3.V_ANCHOR_MV:
        n_ = {k: v for k, v in V.items() if k.startswith(f"V_an{a:02d}_")}; o_ = {k: v for k, v in oV.items() if k.startswith(f"V_an{a:02d}_")}
        if not n_:
            continue
        dies = {}
        for d in P3.B_DIES:
            nd = [m for k, m in n_.items() if f"_d{d}_" in k]; od = [m for k, m in o_.items() if f"_d{d}_" in k]
            dies[d] = dict(new=block(nd)["accuracy"], old=block(od)["accuracy"])
            pc = [m["winner"] for m in nd if m.get("valid")]
            if pc:
                top = max(set(pc), key=pc.count); dies[d]["new_dominant_class_share"] = round(pc.count(top) / len(pc), 4)
        res["3B_V"][f"anchor_{a}mV"] = dict(new=block(list(n_.values())), old=block(list(o_.values())), paired=paired(n_, o_), dies=dies,
                                            new_die_median=float(np.median([v["new"] for v in dies.values()])),
                                            old_die_median=float(np.median([v["old"] for v in dies.values()])))
    (W.SUMM / f"A3_{name}.json").write_text(json.dumps(res, indent=1, default=float))
    return res


if __name__ == "__main__":
    if sys.argv[1] == "run":
        name, which = sys.argv[2], sys.argv[3]
        R.run_pool(jobs(name, which), int(sys.argv[4]) if len(sys.argv) > 4 else 4)
    else:
        r = summary(sys.argv[2])
        print(json.dumps(r, indent=1, default=float)[:8000])
