"""Which device draws go with the logic failures (lockout_failed, stuck_latched) in a size-scaled MC phase (D13 item 2).
Nothing is resized; this only ranks correlations.

For each failing run the class involved is identified from the raw run:
  lockout_failed: every latched class whose trip came after the lock engaged;
  stuck_latched:  every latched class (they latched without a trip edge, i.e. never reset).
z = DVTH / (anchor * sqrt(780/WL)) is each device's standardised V_th draw (same for all samples of a die).
 (a) die level, as asked: per device, point-biserial r between z and 'die fails' (>= 50 % of its runs are
     lockout_failed or stuck_latched). Only n = dies (10), with 134 devices: expect |r| ~ 0.6 by chance alone.
 (b) class level: per device family (the class's own comparator/latch/lock/reset devices, see FAM), r between z and
     'this class is the culprit in >= 1 run of its die', over n = dies x 5 classes.
Usage: python3 failure_devices.py [phase3B_V|phase3B_P]  -> summary/v3/failure_devices_<phase>.json"""
import glob, json, sys
import numpy as np
import common as C
import summarize as SM

PHASE = sys.argv[1] if len(sys.argv) > 1 else "phase3B_V"
PRE = {"phase3B_V": "V_an", "phase3B_P": "P_an"}[PHASE]
# per-class device families: device name for class c (1..5)
FAM = {"M81 sense (ap->d)": lambda c: f"X{81 + 10*(c-1)}", "M82 detect load": lambda c: f"X{82 + 10*(c-1)}",
       "M83 trip driver": lambda c: f"X{83 + 10*(c-1)}", "M84 latch load A": lambda c: f"X{84 + 10*(c-1)}",
       "M85 cross-coupled X": lambda c: f"X{85 + 10*(c-1)}", "M86 cross-coupled Y": lambda c: f"X{86 + 10*(c-1)}",
       "M87 latch load B": lambda c: f"X{87 + 10*(c-1)}", "M88 latch reset": lambda c: f"X{88 + 10*(c-1)}",
       "M89 lock pull-up": lambda c: f"X{89 + 10*(c-1)}", "M90 P_k win pull-up": lambda c: f"X{90 + 10*(c-1)}",
       "XNP na precharge": lambda c: f"XNP{c}", "M75-79 rail reset": lambda c: f"X{74 + c}"}


def pb(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    return float(np.corrcoef(x, y)[0, 1]) if y.std() > 0 and x.std() > 0 else None


if __name__ == "__main__":
    runs = SM.load(PHASE)
    dies = {}
    for m in runs:
        a, d = m["tag"].split("_")[1], m["tag"].split("_")[2]          # anXX, dD
        dies.setdefault((a, d), []).append(m)
    rows, culprit = {}, {}
    for (a, d), rs in sorted(dies.items()):
        dr = json.load(open(sorted(glob.glob(str(C.RAW / PHASE / f"{PRE}{a[2:]}_{d}_s*_draws.json")))[0]))
        anchor = int(a[2:]) / 1000
        z = {k: v["DVTH"] / (anchor * v["sigma_factor"]) for k, v in dr.items()}
        nfail = 0; cc = {c: 0 for c in range(1, 6)}
        for m in rs:
            f = SM.failure(m)
            if f in ("lockout_failed", "stuck_latched"):
                nfail += 1
                for k in m["latched"]:
                    t = m["trip_us"].get(str(k))
                    if f == "stuck_latched" or (t is not None and m.get("lock_us") and t > m["lock_us"]):
                        cc[k] += 1
        rows[(a, d)] = dict(z=z, fail_frac=nfail / len(rs), n=len(rs))
        culprit[(a, d)] = cc
    keys = sorted(rows)
    yd = [rows[k]["fail_frac"] >= 0.5 for k in keys]
    devs = sorted(rows[keys[0]]["z"])
    die_level = sorted(((pb([rows[k]["z"][dv] for k in keys], yd), dv) for dv in devs), key=lambda t: -abs(t[0] or 0))
    cls = {}
    for fam, fn in FAM.items():
        xs, ys = [], []
        for k in keys:
            for c in range(1, 6):
                xs.append(rows[k]["z"][fn(c)]); ys.append(culprit[k][c] > 0)
        cls[fam] = dict(r=pb(xs, ys), n=len(xs), n_culprit=int(sum(ys)),
                        mean_z_culprit=round(float(np.mean([x for x, y in zip(xs, ys) if y])), 3) if any(ys) else None,
                        mean_z_other=round(float(np.mean([x for x, y in zip(xs, ys) if not y])), 3))
    out = dict(phase=PHASE, n_dies=len(keys), n_failing_dies=int(sum(yd)),
               dies={f"{a}_{d}": dict(fail_frac=round(rows[(a, d)]["fail_frac"], 3), culprit_runs_per_class=culprit[(a, d)]) for a, d in keys},
               die_level_top15=[dict(device=dv, r=round(r, 3) if r is not None else None) for r, dv in die_level[:15]],
               die_level_note=f"n = {len(keys)} dies, {len(devs)} devices: |r| of ~0.6-0.7 arises by chance for the top few devices",
               class_level=dict(sorted(cls.items(), key=lambda t: -abs(t[1]["r"] or 0))),
               z_definition="DVTH / (anchor * sqrt(780/WL)); positive = higher |V_th| = weaker p-device")
    (C.SUMM / f"failure_devices_{PHASE}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("n_dies", "n_failing_dies", "die_level_top15")}, indent=0)[:1500])
    for fam, v in out["class_level"].items():
        print(f"{fam:24s} r={v['r']}  culprit {v['n_culprit']}/{v['n']}  mean z culprit {v['mean_z_culprit']} other {v['mean_z_other']}")
