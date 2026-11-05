"""Tooling checks, run before any training (no simulation, no labels, no outcomes are used):
 1. wcommon.build() with the old weights and default timing gives a netlist byte-identical to the campaign's
    common.build() (Variant 3) for the same input vector and warm start.
 2. The same netlist equals the campaign's stored netlist raw/v3/phase1/s31.cir.gz (fetched from Git LFS), i.e. the
    toolchain here reproduces the campaign's build. (Only the netlist text is compared; no result is read.)
 3. apply_mc_paired() with the old weights reproduces the old 3B-V die draws (seed 20001 = anchor 20 mV, die 1)
    for every instance, from raw/v3/phase3B_V/V_an20_d1_s31_draws.json (LFS).
 4. A finger matrix with a different bank pattern builds, and its TFT count is 113 + number of non-empty banks.
 5. Timing arguments reach the netlist (T1 = 220 us moves C2 to 557.5 us).
-> summary/check_tooling.json"""
import gzip, json, re, sys
import numpy as np
import wcommon as W
C = W.C

if __name__ == "__main__":
    out = {}
    wd = C.workdir("wsA_check_v3")
    prior = W.CAMP / "raw/v3/warmstart/fitc10_warm"
    a, b = wd / "mine.cir", wd / "camp.cir"
    W.build(a, W.XTE[31], prior, W.F_OLD)
    C.build(b, 31, prior, variant=3)
    ta, tb = a.read_text(), b.read_text()
    out["1_identical_to_common_build"] = ta == tb
    stored = W.CAMP / "raw/v3/phase1/s31.cir.gz"
    try:
        ts = gzip.open(stored, "rt").read()
        out["2_identical_to_stored_campaign_netlist"] = ts == ta
    except OSError as e:
        out["2_identical_to_stored_campaign_netlist"] = f"not checked: {e}"
    # 3. paired MC draws
    t, draws = W.apply_mc_paired(ta, seed=20001, s_vth=0.020)
    old = json.load(open(W.CAMP / "raw/v3/phase3B_V/V_an20_d1_s31_draws.json"))
    diffs = [abs(draws[k]["DVTH"] - old[k]["DVTH"]) for k in old]
    out["3_paired_draws"] = dict(n_old=len(old), n_new=len(draws), same_names=sorted(old) == sorted(draws),
                                 max_abs_diff_V=max(diffs), all_paired=all(d["paired"] for d in draws.values()))
    # 4. different bank pattern
    F2 = np.array([[30, 0, 0, 10, 0], [0, 30, 0, 10, 0], [30, 0, 30, 10, 20], [0, 30, 30, 10, 0], [0, 0, 0, 10, 20], [0, 0, 0, 10, 20]])
    c = wd / "f2.cir"
    W.build(c, W.XTE[31], prior, F2)
    tc = c.read_text()
    n = sum(1 for l in tc.splitlines() if re.match(r"^X\S+\s.*potft", l))
    xb = {m.group(1): int(float(m.group(2)) / 10) for m in re.finditer(r"^(X\d+)\s+ap\d\s+row\d\s+vdd\s+potftseg\s+W=(\S+)", tc, re.M)}
    ok_map = all(xb.get(f"X{1 + 6 * k + i}", 0) == F2[i, k] for i in range(6) for k in range(5))
    t2, d2 = W.apply_mc_paired(tc, seed=20001, s_vth=0.020)
    out["4_other_pattern"] = dict(n_tft=n, expected=W.n_tft(F2), bank_widths_match=ok_map,
                                  n_unpaired_banks=sum(1 for d in d2.values() if not d["paired"]),
                                  expected_unpaired=int(((F2 > 0) & (W.F_OLD == 0)).sum()))
    # 5. timing
    e = wd / "t1.cir"
    r = W.build(e, W.XTE[31], prior, W.F_OLD, timing=dict(T1=220.0))
    out["5_timing_T1_220"] = dict(tC2=r["tC2"], expected=312.5 + 20 + 220 + 5)
    for p in (a, b, c, e):
        p.unlink()
    (W.SUMM / "check_tooling.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))
