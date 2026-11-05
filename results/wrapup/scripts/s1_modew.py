"""Study 1: mode W robustness (DECISIONS.md S1). Tortoise v1.0 circuit and host protocol v2.1, unchanged.
Usage: python3 s1_modew.py cal | runs | check | forced [nproc]
  cal    : v2.1 calibration sessions of the 9 aging cells and the 5 mismatch dies (each decides its own mode)
  runs   : classification runs (+ the 1 s idle after each mode-W run); cells whose calibration is identical to an
           existing campaign calibration (E1 0.55 V, C3 0.65/0.75 V) get the netlist-identity check and 2 re-simulated
           samples instead of 20 new runs (S1.3)
  check  : netlist-identity check of the reused cells -> summary/s1_identity.json
  forced : secondary S1-F, mode W forced at 0.65 V x mu 1 / 0.7 / 0.5"""
import gzip, json, sys
import wu

AGING = [(round(0.55 + d, 2), m) for d in (0.0, 0.10, 0.20) for m in (1.0, 0.70, 0.50)]
DIES = [dict(anchor=20, die=d, mc=dict(seed=20000 + d, s_vth=0.020, s_mu=0.10, s_rc=0.20, scale="pelgrom_vth"))
        for d in range(1, 6)]
FORCED = [(0.65, m) for m in (1.0, 0.70, 0.50)]
RESIM = (wu.SUB[0], wu.SUB[10])           # re-simulated samples of a reused cell (S1.3)


def ref_cal(vth, muf):
    """Existing calibration of the same corner, no mismatch: E1 (v2.1) for 0.55 V x1, else host_v2 C3 (v2 = mode G)."""
    if (vth, muf) == (0.55, 1.0):
        return wu.HV21RAW / "cal/v0550_m100/calibration.json", wu.HV21RAW / "E1", "E1_v0550_m100_v21_s{:02d}"
    k = f"v{round(vth*1000):04d}_m{round(muf*100):03d}"
    f = wu.HV2RAW / f"cal/{k}/calibration.json"
    return (f, wu.HV2RAW / "C3", f"C3_{k}_learned_s{{:02d}}") if f.exists() else (None, None, None)


def cals():
    a = [dict(key=wu.ckey("S1", v, m), vth=v, muf=m) for v, m in AGING]
    a += [dict(key=wu.ckey("S1", 0.55, 1.0, die=d), vth=0.55, muf=1.0, mc=d["mc"]) for d in DIES]
    return a


def reused(c):
    f, _, _ = ref_cal(c["vth"], c["muf"])
    return bool(f) and c["mc"] is None and wu.same_calibration(c, json.load(open(f)))


def jobs():
    from multiprocessing import Pool
    with Pool(4) as p:
        cs = p.map(wu.cal_job, cals())
    out = []
    for c in cs:
        if c.get("failed"):
            print("calibration failed:", c["key"]); continue
        idx = RESIM if reused(c) else wu.SUB
        out += [wu.cls_job("S1", c, i, idle=(c["mode"] == "W" and c["mc"] is None)) for i in idx]   # S1-D1: no idles on mismatch dies
    return out


def check():
    """For each reused cell: the 20 classification netlists built for this study vs the stored reference netlists
    (LFS .cir.gz), compared with the corner .lib path reduced to its file name; plus the .lib files themselves."""
    res = {}
    for a in cals():
        c = wu.calibrate(**a)
        if not reused(c):
            continue
        f, rdir, pat = ref_cal(c["vth"], c["muf"])
        same, diff = 0, []
        for i in wu.SUB:
            j = wu.cls_job("S1", c, i)
            mine = wu.norm_lib(wu.build_cls_text(j))
            ref = wu.norm_lib(gzip.open(rdir / (pat.format(i) + ".cir.gz"), "rt").read())
            if mine == ref:
                same += 1
            else:
                diff.append(i)
        res[c["key"]] = dict(reference_calibration=str(f.relative_to(wu.REPO)), reference_runs=str(rdir.relative_to(wu.REPO)),
                             netlists_identical=same, n=len(wu.SUB), differing=diff, mode=c["mode"])
    json.dump(res, open(wu.SUMM / "s1_identity.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    w = sys.argv[1]
    n = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 4
    if w == "cal":
        from multiprocessing import Pool
        with Pool(n) as p:
            for c in p.imap_unordered(wu.cal_job, cals()):
                print(c["key"], c.get("mode"), c.get("vhat"), c.get("k"), c.get("flag"), "reused" if reused(c) else "", flush=True)
    elif w == "runs":
        wu.pool_run(jobs(), n)
    elif w == "check":
        check()
    elif w == "forced":
        from multiprocessing import Pool
        with Pool(n) as p:
            cs = p.map(wu.cal_job, [dict(key=wu.ckey("S1F", v, m, forced="W"), vth=v, muf=m, force_mode="W") for v, m in FORCED])
        wu.pool_run([wu.cls_job("S1F", c, i, idle=True) for c in cs for i in wu.SUB], n)
