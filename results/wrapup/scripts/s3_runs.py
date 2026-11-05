"""Study 3 SPICE runs for R10.2-bias (DECISIONS S3). Host protocol v2.1 at the nominal die (mode G), every weight set its
own design-time run and calibration session.
Usage: python3 s3_runs.py design <wname>          design-time nominal run of the variant (constants, S3.2 rule)
       python3 s3_runs.py K [nproc]               40 K training samples with the probe matrix (S3.2)
       python3 s3_runs.py recal                   fit the v2.1 surrogate parameters -> summary/s3_surrogate_params.json
       python3 s3_runs.py S <wname> ... [nproc]   40 held-out S training samples per finalist (S3.3)
       python3 s3_runs.py test [nproc]            the frozen choice on the 90 test samples (S3.4; refuses unless frozen)
       python3 s3_runs.py mm [nproc]              3B-V 20 mV, the 5 C4 dies paired by instance (S3.4)
       python3 s3_runs.py stress                  C2-procedure stress audit, 5 runs (S3.4)
Weight sets: weights/<wname>.npz (F6, Fb)."""
import gzip, hashlib, json, pathlib, subprocess, sys
import numpy as np
import wu, hv21, hv2, eh, common as C
import s3_variant as V

WD = wu.WU / "weights"
DIES = [dict(anchor=20, die=d, seed=20000 + d, s_vth=0.020) for d in range(1, 4)]      # S3-D2: first 3 of the 5 C4 dies
REV_DESIGN = json.load(open(wu.HV2RAW.parent / "summary/design_constants.json"))
SPL = json.loads((wu.REPO / "results/weights_schemeA/summary/splits.json").read_text())
FROZEN = WD / "FROZEN_S3.json"
_G = dict(zip(SPL["S"], [None] * len(SPL["S"])))
S20 = [i for i in SPL["S"] if int(C.D["group_train"][i]) in SPL["S_groups"][:2]]      # S3-D1: groups 3 and 4 (20 samples)


def load_w(wname):
    z = np.load(WD / f"{wname}.npz")
    return z["F6"], z["Fb"]


def variant(wname):
    F6, Fb = load_w(wname)
    return V.register(f"bias_{wname}", Fb, F6)


def set_energy(job):
    if job.get("variant", "").startswith("bias_"):
        V.use_row7_energy()


def run_job(job):
    set_energy(job)
    die = job.get("die")
    wu.set_context(variant=job["variant"], in_cal=False, die=die)
    return hv21.run_cls(job)


def design(wname):
    """Design-time run of the variant on the nominal die (V_hat := 0.65 V, mu_hat := 1; S3.2). Returns the constants
    the variant's calibrations use: Tortoise v1.0's if the variant's a1 offset and I_ref agree within 0.1 mV / 0.1 %, else
    its own (c_a1, I_ref, c_race)."""
    f = wu.SUMM / f"s3_design_{wname}.json"
    if f.exists():
        return json.load(open(f))
    v = variant(wname)
    V.use_row7_energy()
    wu.set_context(variant=v.name, in_cal=True, die=None)
    rec = hv21.calibrate(f"S3design_{wname}", 0.65, 1.0, None, nominal=True)
    wu.set_context(in_cal=False)
    own = dict(a1_offset_V=rec["a1"]["vraw"] - 0.65, I_ref_uA=rec["a1"]["i_ov_uA"], race_offset_V=rec["race"]["vraw"] - 0.65)
    same = (abs(own["a1_offset_V"] - REV_DESIGN["a1_offset_V"]) < 1e-4
            and abs(own["I_ref_uA"] / REV_DESIGN["I_ref_uA"] - 1) < 1e-3)
    use = {k: REV_DESIGN[k] for k in own} if same else own
    out = dict(weights=wname, own=own, rev10_1={k: REV_DESIGN[k] for k in own}, reuse_rev10_1=same, use=use,
               n_tft=v.n_tft(), race_t_us=rec["race"]["t_us"])
    json.dump(out, open(f, "w"), indent=1, default=float)
    return out


def calib(wname, key, mc_die=None):
    d = design(wname)
    v = variant(wname)
    V.use_row7_energy()
    wu.set_context(variant=v.name, in_cal=True, die=mc_die)
    old = dict(hv21.DESIGN_V2)
    try:
        hv21.DESIGN_V2.update(d["use"])
        c = hv21.calibrate(key, 0.65, 1.0, None)
    finally:
        hv21.DESIGN_V2.clear(); hv21.DESIGN_V2.update(old)
        wu.set_context(in_cal=False, die=None)
    return c


def jobs_train(phase, wname, idxs, c, die=None):
    v = variant(wname)
    out = []
    for i in idxs:
        j = dict(tag=f"{phase}_{wname}_tr{i:03d}", idx=None, x=C.D["X_train"][i], label=int(C.D["y_train"][i]) + 1,
                 outdir=wu.RAW / phase, wdir=f"wu_{phase}", vth=0.65, muf=1.0, mc=None, V1=c["levels"][0], V2=c["levels"][1],
                 k=c["k"], mode=c["mode"], prior_state=c["start_state"], vth_metric=0.65, variant=v.name, policy="v2.1",
                 cal_key=c["key"], split="train", train_idx=int(i), weights=wname)
        out.append(j)
    return out


def jobs_test(phase, wname, idxs, c, die=None, tagx=""):
    v = variant(wname)
    return [dict(tag=f"{phase}_{wname}{tagx}_s{i:02d}", idx=int(i), outdir=wu.RAW / phase, wdir=f"wu_{phase}", vth=0.65, muf=1.0,
                 mc=None, V1=c["levels"][0], V2=c["levels"][1], k=c["k"], mode=c["mode"], prior_state=c["start_state"],
                 vth_metric=0.65, variant=v.name, policy="v2.1", cal_key=c["key"], split="test", weights=wname, die=die)
            for i in idxs]


def frozen():
    """The frozen choice; refuses unless weights file matches the committed SHA-256 at HEAD."""
    rec = json.load(open(FROZEN))
    f = WD / f"{rec['weights']}.npz"
    assert hashlib.sha256(f.read_bytes()).hexdigest() == rec["sha256"], "weights differ from the frozen record"
    head = subprocess.run(["git", "show", f"HEAD:results/wrapup/weights/{rec['weights']}.npz"], cwd=wu.REPO, capture_output=True).stdout
    assert hashlib.sha256(head).hexdigest() == rec["sha256"], "frozen weights are not committed at HEAD"
    return rec["weights"]


# ----------------------------------------------------------------------------- recalibration fit (S3.2)
def wave(f):
    with gzip.open(f, "rt") as g:
        h = g.readline().strip().split(",")
        d = np.loadtxt(g, delimiter=",")
    return {k: d[:, i] for i, k in enumerate(h)}


def recal():
    import s3_train as TR
    F6, Fb = load_w("S3_probe")
    runs = [json.load(open(f)) for f in sorted((wu.RAW / "S3K").glob("S3K_*.json"))]
    q0 = TR.params("retrain_study")
    rows = []
    for m in runs:
        x = np.array(C.D["X_train"][m["job"]["train_idx"]])
        w = wave(wu.RAW / "S3K" / f"{m['tag']}.csv.gz")
        t = w["t_us"]; tc2 = m["build"]["tC2"]
        tend = (min(float(v) for v in m["trip_us"].values()) - 5.0) if m.get("trip_us") else m["t_read_us"] - 5.0
        sl = (t >= tc2 + 20) & (t <= tend)
        for k in range(5):
            drive = 170.0 * float(x @ F6[:, k]) + 20.0 * float(F6[:, k].sum())
            bias = float(Fb[k]) * (20.0 + V.XB * 170.0)
            slope = float(np.polyfit(t[sl], w[f"ap{k+1}"][sl], 1)[0]) if sl.sum() > 10 else None
            rows.append(dict(tag=m["tag"], k=k, drive=drive, bias=bias, V=float(m["rail_at_C2"][str(k + 1)]), slope=slope,
                             n=float(F6[:, k].sum()), won=(m.get("first") == k + 1), race=m.get("race_us"),
                             label=m["label"], valid=bool(m.get("valid_read")), first=m.get("first"), gap=m.get("gap")))
    A = np.array([[1.0, r["drive"], r["bias"]] for r in rows]); y = np.array([r["V"] for r in rows])
    (R0, alpha, alpha_b), *_ = np.linalg.lstsq(A, y, rcond=None)
    res = y - A @ np.array([R0, alpha, alpha_b])
    sl = [(r["n"], r["slope"]) for r in rows if r["slope"] is not None]
    gamma = float(np.sum([a * b for a, b in sl]) / np.sum([a * a for a, b in sl]))
    Th = {}
    for r in rows:
        if r["won"] and r["race"] is not None:
            Th.setdefault(r["k"], []).append(r["V"] + gamma * r["n"] * r["race"])
    Theta = [float(np.median(Th[k])) if k in Th else float(np.median(sum(Th.values(), []))) for k in range(5)]
    q = dict(R=[float(R0)] * 5, alpha=float(alpha), alpha_b=float(alpha_b), c0=0.0, gamma=gamma, Theta=Theta,
             G_res=q0["G_res"], T1=170.0, WMIN=20.0, gap_factor=1.0, XB=V.XB)
    # gap factor: SPICE gap estimate (runner-up rail deficit at the trip / local slope; metrics_v2 'gap_slope_us') over
    # the surrogate's raw runner-up gap, median over runs with the same winner and runner-up
    qq = dict(q, R=np.array(q["R"]), Theta=np.array(Theta))
    ratios, agree = [], dict(winner=0, valid=0, outcome=0, n=0)
    for m in runs:
        x = np.array(C.D["X_train"][m["job"]["train_idx"]])[None]
        tt, c1 = TR.race(F6, Fb, x, qq)
        tt = tt[0, 0]
        o = np.argsort(tt)
        g_sur = float(tt[o[1]] - tt[o[0]])
        if m.get("first") == o[0] + 1 and m.get("runner_up") == o[1] + 1 and m.get("gap", {}).get("gap_slope_us"):
            ratios.append(m["gap"]["gap_slope_us"] / g_sur)
    gf = float(np.median(ratios)) if ratios else 1.0
    q["gap_factor"] = gf
    qq["gap_factor"] = gf
    for m in runs:
        x = np.array(C.D["X_train"][m["job"]["train_idx"]])[None]
        tt, c1 = TR.race(F6, Fb, x, qq)
        tt = tt[0, 0]; o = np.argsort(tt)
        win_s = int(o[0]) + 1; valid_s = (tt[o[1]] - tt[o[0]] >= q["G_res"]) and not c1[0, 0]
        corr_s = valid_s and win_s == m["label"]
        corr = bool(m.get("valid_read")) and m.get("winner_read") == m["label"]
        agree["n"] += 1
        agree["winner"] += int(win_s == m.get("first"))
        agree["valid"] += int(valid_s == bool(m.get("valid_read")))
        agree["outcome"] += int(corr_s == corr)
    out = dict(nominal=q, fit=dict(rails=len(rows), rms_residual_mV=float(np.sqrt(np.mean(res ** 2)) * 1e3),
                                   alpha_b_over_alpha=float(alpha_b / alpha), slopes=len(sl), gap_ratios=len(ratios),
                                   theta_counts={k: len(v) for k, v in Th.items()}),
               agreement_in_sample=agree, retrain_study_nominal={k: (list(v) if isinstance(v, np.ndarray) else v) for k, v in q0.items()},
               source="raw/S3K (40 K training samples, probe weights/S3_probe.npz, v2.1 nominal)")
    TR.PFILE.write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    w = sys.argv[1]
    n = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 4
    if w == "design":
        print(json.dumps(design(sys.argv[2]), indent=1, default=float))
    elif w == "K":
        c = calib("S3_probe", "S3_nominal_S3_probe")
        wu.pool_run(jobs_train("S3K", "S3_probe", SPL["K"], c), n, fn=run_job)
    elif w == "recal":
        recal()
    elif w == "S":
        js = []
        for wn in [a for a in sys.argv[2:] if not a.isdigit()]:
            c = calib(wn, f"S3_nominal_{wn}")
            js += jobs_train("S3S", wn, S20, c)
        wu.pool_run(js, n, fn=run_job)
    elif w == "test":
        wn = frozen()
        c = calib(wn, f"S3_nominal_{wn}")
        wu.pool_run(jobs_test("S3test", wn, range(90), c), n, fn=run_job)
    elif w == "stress":
        import wu_stress
        wn = frozen()
        F6, Fb = load_w(wn)
        v = variant(wn)
        scores = C.XTE @ F6 + Fb[None, :] * (hv2.WMIN / hv2.T1_BASE + V.XB)
        wu_stress.audit(v.name, calib(wn, f"S3_nominal_{wn}"), f"s3_stress_{wn}", scores=scores)
    elif w == "mm":
        wn = frozen()
        from multiprocessing import Pool
        js = []
        for d in DIES:
            c = calib(wn, f"S3_mm_{wn}_an20d{d['die']:02d}", mc_die=d)
            js += jobs_test("S3mm", wn, wu.SUB, c, die=d, tagx=f"_an20d{d['die']:02d}")
        wu.pool_run(js, n, fn=run_job)
