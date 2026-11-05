"""Mismatch-injection calibration (DECISIONS.md W4.3) and the mismatch check (W4.4). Training samples in K only.
W4.3: each one-device run (raw/sens_old) is paired with the nominal run of the same sample (raw/K_old). The winner's
      trip-time shift dt [us] is converted to an effective trip-level shift dTheta = dt * s_g (s_g = the fitted gap
      slope, so that the surrogate's margin moves by exactly dt); coefficient = dTheta / dV_th. For the reset switch the measured reset-level shift is reported
      as well; the race coefficient is the timing-based one (-dt * s_g / dV_th, the rail starts higher by that much).
      Devices measured at +/-30 mV use the two-sided slope. The crossbar bank is not fitted: the surrogate's prediction
      from the bank_dc.py curves is compared with SPICE.
W4.4: raw/mm_old (3 paired dies x 10 K samples, anchor 35 mV): the surrogate is fed the same per-instance draws
      (from the *_draws.json files) and its winner/validity is compared with SPICE.
-> summary/surrogate_params.json (keys chain, reset), summary/A0_mismatch.json"""
import gzip, json, re
import numpy as np
import wcommon as W
import surrogate as SG

ROLE = {81: "sense", 82: "detect_load", 83: "trip_driver", 84: "latch_load_A", 85: "cross_X", 86: "cross_Y", 87: "latch_load_B"}


def areas(netlist_text):
    return {m.group(1): float(m.group(2)) * float(m.group(3)) for m in
            re.finditer(r"^(X\S+)\s+\S+\s+\S+\s+\S+\s+potft(?:seg)?\s+W=(\S+)\s+L=(\S+)", netlist_text, re.M)}


def chain_fit():
    sel = json.loads((W.SUMM / "sens_selection.json").read_text())
    base = json.loads((W.RAW / "K_old" / f"{sel['base_tag']}.json").read_text())
    c = sel["winner"]
    q = SG.corner_params(0.65)
    sg = 60 * q["gamma"] / q.get("gap_factor", 1.0)        # s_g: margins are gap_factor * dTheta / s_bar = dTheta / s_g
    tb = base["trip_us"][str(c)]
    runs = [json.loads(f.read_text()) for f in sorted((W.RAW / "sens_old").glob("*.json"))]
    net = gzip.open(W.RAW / "K_old" / f"{sel['base_tag']}.cir.gz", "rt").read()
    A = areas(net)
    meas = {}
    for m in runs:
        (dev, dv), = m["perturb"].items()
        ok = m.get("valid") and m.get("winner") == c
        dt = m["trip_us"][str(c)] - tb if ok else None
        meas.setdefault(dev, {})[dv] = dict(valid=bool(m.get("valid")), winner=m.get("winner"), dt_us=dt,
                                           d_reset_mV=round((m["reset_level"][str(c)] - base["reset_level"][str(c)]) * 1e3, 3),
                                           d_rail_at_C2_mV=round((m["rail_at_C2"][str(c)] - base["rail_at_C2"][str(c)]) * 1e3, 3))
    chain, reset, bank = {}, None, None
    for dev, d in meas.items():
        n = int(dev[1:])
        if n <= 30:                                        # crossbar bank
            bank = (dev, d)
            continue
        if all(v["dt_us"] is not None for v in d.values()):
            dvs = sorted(d)
            slope = (d[dvs[-1]]["dt_us"] - d[dvs[0]]["dt_us"]) / (dvs[-1] - dvs[0]) if len(dvs) > 1 else d[dvs[0]]["dt_us"] / dvs[0]
        else:
            slope = None
        if 75 <= n <= 79:
            reset = dict(device=dev, area=A[dev], coef=-slope * sg if slope is not None else None, measured=d,
                         reset_level_coef=np.mean([v["d_reset_mV"] / 1e3 / k for k, v in d.items()]))
        else:
            role = ROLE[81 + (n - 81) % 10]
            chain[role] = dict(device=dev, area=A[dev], coef=slope * sg if slope is not None else 0.0, measured=d,
                               linearity=(None if len(d) < 2 else dict(dt_plus=d[max(d)]["dt_us"], dt_minus=d[min(d)]["dt_us"])))
    # bank check: surrogate prediction of the winner's trip shift for the perturbed bank
    bdev, bd = bank
    j = int(bdev[1:]) - 1; k, i = j // 6, j % 6
    F = np.array(base["F"]); x = np.array(base["x"])[None]
    t0, _ = SG.race(F, x, q)
    g1 = np.ones((1, 6, 5)); g2 = np.ones((1, 6, 5)); dv = list(bd)[0]
    g1[0, i, k] = SG.g_of(dv, 1); g2[0, i, k] = SG.g_of(dv, 2)

    class _D:                                              # one fixed die with only this bank perturbed
        n = 1
        def bank_factors(self, F_):
            return g1, g2
        def offsets(self):
            return np.zeros((1, 5)), np.zeros((1, 5))
    t1, _ = SG.race(F, x, q, _D())
    bank_check = dict(device=bdev, fingers=int(F[i, k]), dvth=dv, spice_dt_us=bd[dv]["dt_us"],
                      surrogate_dt_us=float(t1[0, 0, k] - t0[0, 0, k]),
                      spice_d_rail_at_C2_mV=bd[dv]["d_rail_at_C2_mV"])
    return dict(selection=sel, s_g_V_per_us=sg, chain=chain, reset=reset, bank_check=bank_check)


def mm_check():
    runs = W.load_runs("mm_old")
    q = SG.corner_params(0.65); p = SG.params()
    rows = []
    for m in runs:
        dr = json.loads((W.RAW / "mm_old" / f"{m['tag']}_draws.json").read_text())
        F = np.array(m["F"]); x = np.array(m["x"])[None]
        g1 = np.ones((1, 6, 5)); g2 = np.ones((1, 6, 5))
        for i in range(6):
            for k in range(5):
                nm = f"X{1 + 6 * k + i}"
                if nm in dr:
                    g1[0, i, k] = SG.g_of(dr[nm]["DVTH"], 1); g2[0, i, k] = SG.g_of(dr[nm]["DVTH"], 2)
        dR = np.array([[p["reset"]["coef"] * dr[f"X{75 + k}"]["DVTH"] for k in range(5)]])
        dT = np.zeros((1, 5))
        for role, cdef in p["chain"].items():
            n0 = int(cdef["device"][1:]); base = 81 + (n0 - 81) % 10
            for k in range(5):
                dT[0, k] += cdef["coef"] * dr[f"X{base + 10 * k}"]["DVTH"]

        class _D:
            n = 1
            def bank_factors(self, F_):
                return g1, g2
            def offsets(self):
                return dR, dT
        w, gap, r, c1 = SG.predict(F, x, q, _D())
        sv = bool(gap[0, 0] >= q["G_res"]) and not c1[0, 0]
        rows.append(dict(tag=m["tag"], label=m["label"], spice_first=m.get("first"), spice_valid=bool(m.get("valid")),
                         spice_correct=bool(m.get("valid")) and m.get("winner") == m["label"], spice_gap=(m.get("gap") or {}).get("gap_reach_us"),
                         sur_first=int(w[0, 0]) + 1, sur_gap=round(float(gap[0, 0]), 2), sur_valid=sv,
                         sur_correct=sv and int(w[0, 0]) + 1 == m["label"]))
    # same samples at nominal (K_old) for reference: how many winners did the die change?
    K = {m["idx"]: m for m in W.load_runs("K_old")}
    for r in rows:
        idx = int(r["tag"].split("_tr")[1])
        r["nominal_spice_first"] = K[idx].get("first")
    n = len(rows)
    return dict(n=n, first_agree=sum(r["spice_first"] == r["sur_first"] for r in rows),
                correct_agree=sum(r["spice_correct"] == r["sur_correct"] for r in rows),
                validity_agree=sum(r["spice_valid"] == r["sur_valid"] for r in rows),
                spice_correct=sum(r["spice_correct"] for r in rows), sur_correct=sum(r["sur_correct"] for r in rows),
                n_winner_changed_by_die_spice=sum(r["spice_first"] != r["nominal_spice_first"] for r in rows),
                n_winner_changed_by_die_surrogate_agrees=sum((r["spice_first"] != r["nominal_spice_first"]) and r["sur_first"] == r["spice_first"] for r in rows),
                rows=rows)


if __name__ == "__main__":
    out = {}
    cf = chain_fit()
    out["chain_fit"] = cf
    p = json.loads(SG.PFILE.read_text())
    p["chain"] = {k: dict(device=v["device"], area=v["area"], coef=v["coef"]) for k, v in cf["chain"].items()}
    p["reset"] = dict(device=cf["reset"]["device"], area=cf["reset"]["area"], coef=cf["reset"]["coef"])
    SG.PFILE.write_text(json.dumps(p, indent=1)); SG.reload()
    if any((W.RAW / "mm_old").glob("*.json")):
        out["mm_check"] = mm_check()
    (W.SUMM / "A0_mismatch.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "rows"} for k, v in out.items()}, indent=1, default=float)[:5000])
