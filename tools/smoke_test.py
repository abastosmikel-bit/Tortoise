#!/usr/bin/env python3
"""Tortoise v1.0 smoke test: five real ngspice runs that must reproduce recorded outcomes.

Run through tools/smoke_test.sh (it sets up the /home/claude/w layout first). Nothing is written inside the repository:
netlists and waveforms go to /home/claude/w/sim/smoke_* and the per-run JSONs to $SMOKE_OUT (default
/tmp/tortoise_smoke). The recorded outcomes are read from committed per-run JSONs; no campaign result is modified.

Tests (expected = the committed run named in each line):
  lab81    lab corner (lab_vth085), lab-corner build of #81 with the borrowed prior t6L_x2_v085
           expected: results/fitc10_campaign/summary/smoke_lab_s81.json
  v3_81    fitc10 Variant 3, #81, Variant 3 warm start, 2500 us window
           expected: results/fitc10_campaign/raw/v3/phase1/s81.json
  v3_31    same, #31 (the closest valid near tie of Phase 1: runner-up gap 10.7 us)
           expected: results/fitc10_campaign/raw/v3/phase1/s31.json
  v21_nom  host protocol v2.1 at the nominal die (0.65 V -> mode G = v2), sample #1, start state and levels from the
           v2.1 nominal calibration (results/host_v21/raw/cal/v0650_m100/calibration.json)
           expected: results/host_v2/raw/C3/C3_v0650_m100_learned_s01.json (same start state, levels and k)
  v21_W51  host protocol v2.1 at |V_th| 0.51 V (mode W), sample #1, job of results/host_v21/raw/E1/E1_v0510_m100_v21_s01.json
           expected: that file
Match rule: same latched set, validity and failure label, and every recorded time (trip, lock latency, race, read)
within TOL_US. Prints a table and writes $SMOKE_OUT/smoke_summary.json. Exit code 0 only if all five match.
"""
import json, os, pathlib, re, subprocess, sys, time
from multiprocessing import Pool

sys.dont_write_bytecode = True
REPO = pathlib.Path(__file__).resolve().parents[1]
RES = REPO / "results"
W = pathlib.Path("/home/claude/w")
OUT = pathlib.Path(os.environ.get("SMOKE_OUT", "/tmp/tortoise_smoke"))
TOL_US = 0.05


def _close(a, b):
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= TOL_US


def t_lab81():
    """The lab-corner builder smoke test (docs/TOOLING.md §4) and fitc10_campaign/scripts/smoke_lab.sh, into a scratch dir."""
    exp = json.load(open(RES / "fitc10_campaign/summary/smoke_lab_s81.json"))
    wd = W / "sim/circuits"
    net = wd / "smoke_rev10_1_lab81.cir"
    env = dict(os.environ, OUT=str(net), PYTHONDONTWRITEBYTECODE="1")
    b = subprocess.run([sys.executable, "../tools/build_A.py", "81", "t6L_x2_v085"], cwd=wd, env=env,
                       capture_output=True, text=True, check=True).stdout.strip()
    s = time.time()
    subprocess.run([sys.executable, "../tools/run_diag.py", net.name, "smoke_rev10_1_lab81"], cwd=wd,
                   env=dict(env, RELAX="1"), capture_output=True, text=True, check=True)
    wall = time.time() - s
    sys.path.insert(0, str(W / "sim/tools"))
    cwd = os.getcwd()
    os.chdir(wd)
    try:
        from score import score
        r = score("smoke_rev10_1_lab81", t_on=320e-6, expect=5, t_off=5000e-6)
    finally:
        os.chdir(cwd)
    got = dict(build_msg=b, n_tft=sum(1 for l in open(net) if l.startswith("X")),
               trip_us=float(r["trip"]) * 1e6 if r["trip"] else None, latched=r["latched"],
               lock_latency_us=float(r["lat"]), valid=bool(r["valid"]))
    ok = (got["n_tft"] == exp["n_tft"] and "507.5" in b and str(got["latched"]) == str(exp["latched"])
          and got["valid"] == exp["valid"] and _close(got["trip_us"], exp["trip_us"])
          and _close(got["lock_latency_us"], exp["lock_latency_us"]))
    keep = ("n_tft", "trip_us", "latched", "lock_latency_us", "valid")
    return dict(test="lab81", ok=ok, wall_s=round(wall, 1), got=got, expected={k: exp[k] for k in keep},
                expected_file="results/fitc10_campaign/summary/smoke_lab_s81.json")


def _v3(idx):
    sys.path.insert(0, str(RES / "fitc10_campaign/scripts"))
    os.environ["FC10_VARIANT"] = "3"
    import common as C
    ef = RES / f"fitc10_campaign/raw/v3/phase1/s{idx:02d}.json"
    exp = json.load(open(ef))
    m = C.run_one(dict(tag=f"smoke_v3_s{idx:02d}", idx=idx, prior=RES / "fitc10_campaign/raw/v3/warmstart/fitc10_warm",
                       variant=3, outdir=OUT, wdir="smoke"))
    keep = ("n_tft", "trip_us", "first", "latched", "valid", "failure", "lock_latency_us", "tC2_us")
    m["trip_us"] = {str(k): v for k, v in m.get("trip_us", {}).items()}   # json keys are strings
    ok = (m.get("latched") == exp["latched"] and m.get("valid") == exp["valid"] and m.get("failure") == exp["failure"]
          and m.get("n_tft") == exp["n_tft"] and set(m["trip_us"]) == set(exp["trip_us"])
          and all(_close(m["trip_us"][k], exp["trip_us"][k]) for k in exp["trip_us"])
          and _close(m.get("lock_latency_us"), exp["lock_latency_us"]))
    return dict(test=f"v3_{idx}", ok=ok, wall_s=m["run"]["wall_s"], got={k: m.get(k) for k in keep},
                expected={k: exp[k] for k in keep}, expected_file=str(ef.relative_to(REPO)))


def _v21(tag, job, ef):
    sys.path.insert(0, str(RES / "host_v21/scripts"))
    import hv21
    exp = json.load(open(ef))
    job = dict(job, tag=tag, outdir=OUT, wdir="smoke")
    m = hv21.run_cls(job)
    keep = ("mode", "race_us", "latched_read", "valid_read", "failure_read", "t_read_us")
    ok = (m.get("latched_read") == exp["latched_read"] and m.get("valid_read") == exp["valid_read"]
          and m.get("failure_read") == exp["failure_read"] and _close(m.get("race_us"), exp["race_us"])
          and _close(m.get("t_read_us"), exp["t_read_us"]))
    return dict(got={k: m.get(k) for k in keep}, expected={k: exp.get(k) for k in keep}, ok=ok,
                wall_s=m["run"]["wall_s"], expected_file=str(pathlib.Path(ef).relative_to(REPO)))


def t_v21_nom():
    cal = json.load(open(RES / "host_v21/raw/cal/v0650_m100/calibration.json"))
    assert cal["mode"] == "G"
    V1, V2 = cal["levels"]
    job = dict(idx=1, vth=0.65, muf=1.0, mc=None, V1=V1, V2=V2, k=cal["k"], mode=cal["mode"],
               prior_state=cal["start_state"], vth_metric=0.65)
    r = _v21("smoke_v21_nom_s01", job, RES / "host_v2/raw/C3/C3_v0650_m100_learned_s01.json")
    r["expected"]["mode"] = "G"     # host_v2 runs carry no mode field; v2 is mode G by definition (P2.2)
    r["ok"] = r["ok"] and r["got"]["mode"] == "G"
    return dict(test="v21_nom", **r)


def t_v21_W51():
    ef = RES / "host_v21/raw/E1/E1_v0510_m100_v21_s01.json"
    e = json.load(open(ef))
    j = e["job"]
    job = dict(idx=j["idx"], vth=j["vth"], muf=j["muf"], mc=j["mc"], V1=j["V1"], V2=j["V2"], k=j["k"], mode=j["mode"],
               prior_state=e["prior_state"], vth_metric=j["vth_metric"])
    r = _v21("smoke_v21_W051_s01", job, ef)
    r["ok"] = r["ok"] and r["got"]["mode"] == "W"
    return dict(test="v21_W51", **r)


TESTS = dict(lab81=t_lab81, v3_81=lambda: _v3(81), v3_31=lambda: _v3(31), v21_nom=t_v21_nom, v21_W51=t_v21_W51)


def run(name):
    s = time.time()
    try:
        r = TESTS[name]()
    except Exception as e:  # a crash is a failed smoke test, reported as such
        r = dict(test=name, ok=False, error=f"{type(e).__name__}: {e}")
    r["elapsed_s"] = round(time.time() - s, 1)
    return r


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("smoke_*.json"):      # run_cls/run_one would otherwise reuse a cached result
        f.unlink()
    names = sys.argv[1:] or list(TESTS)
    nproc = int(os.environ.get("SMOKE_NPROC", "4"))
    s = time.time()
    with Pool(min(nproc, len(names))) as p:
        res = p.map(run, names)
    total = round(time.time() - s, 1)
    ver = subprocess.run(["ngspice", "--version"], capture_output=True, text=True).stdout
    ver = (re.search(r"ngspice-\S+", ver) or [None])[0]
    print(f"{'test':10s} {'result':7s} {'sim wall s':>10s}  got / expected")
    for r in res:
        print(f"{r['test']:10s} {'MATCH' if r['ok'] else 'DIFFER':7s} {str(r.get('wall_s', '-')):>10s}  "
              f"{r.get('got', r.get('error'))}\n{'':30s}{r.get('expected', '')}")
    summary = dict(all_match=all(r["ok"] for r in res), total_wall_s=total, nproc=nproc, ngspice=ver, tol_us=TOL_US,
                   tests=res)
    (OUT / "smoke_summary.json").write_text(json.dumps(summary, indent=1, default=str))
    print(f"ALL MATCH: {summary['all_match']}   total wall time {total} s on {nproc} processes ({ver})")
    sys.exit(0 if summary["all_match"] else 1)
