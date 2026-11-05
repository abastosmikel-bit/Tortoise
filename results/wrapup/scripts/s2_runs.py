"""Study 2 evaluation runs (DECISIONS S2.2-S2.3). Host protocol v2.1 unchanged; circuit = a named variant.
Usage: python3 s2_runs.py design <variant>
       python3 s2_runs.py edge <variant> [nproc]     0.65 V first (nominal check), then 0.49, 0.51, 0.47, 0.45 V
       python3 s2_runs.py nominal90 <variant> [nproc] the best variant on all 90 test samples (S2.3)
       python3 s2_runs.py stress <variant>          C2-procedure stress audit (S2.3)"""
import json, sys
import wu, hv21, hv2
import s2_variants as SV

REV_DESIGN = json.load(open(wu.HV2RAW.parent / "summary/design_constants.json"))
ORDER = (0.65, 0.49, 0.51)            # phase 1, both variants (S2-D2)
ORDER2 = (0.47, 0.45)                 # phase 2, the better variant only (S2-D2)


def design(var):
    f = wu.SUMM / f"s2_design_{var}.json"
    if f.exists():
        return json.load(open(f))
    wu.set_context(variant=var, in_cal=True)
    rec = hv21.calibrate(f"S2design_{var}", 0.65, 1.0, None, nominal=True)
    wu.set_context(in_cal=False)
    own = dict(a1_offset_V=rec["a1"]["vraw"] - 0.65, I_ref_uA=rec["a1"]["i_ov_uA"], race_offset_V=rec["race"]["vraw"] - 0.65)
    same = abs(own["a1_offset_V"] - REV_DESIGN["a1_offset_V"]) < 1e-4 and abs(own["I_ref_uA"] / REV_DESIGN["I_ref_uA"] - 1) < 1e-3
    out = dict(variant=var, own=own, rev10_1={k: REV_DESIGN[k] for k in own}, reuse_rev10_1=same,
               use={k: REV_DESIGN[k] for k in own} if same else own, race_t_us=rec["race"]["t_us"])
    json.dump(out, open(f, "w"), indent=1, default=float)
    return out


def cal(var, vth):
    return wu.calibrate(wu.ckey("S2", vth, 1.0, variant=var), vth, 1.0, None, variant=var, design=design(var)["use"])


def outcome(m):
    return (tuple(m.get("latched_read") or []), bool(m.get("valid_read")), m.get("failure_read"))


def nominal_ok(var):
    c = cal(var, 0.65)
    bad = []
    for i in wu.SUB:
        a = json.load(open(wu.RAW / "S2" / f"S2_{c['key']}_v21_s{i:02d}.json"))
        b = json.load(open(wu.HV2RAW / "C3" / f"C3_v0650_m100_learned_s{i:02d}.json"))
        if outcome(a) != outcome(b):
            bad.append(i)
    return bad


if __name__ == "__main__":
    w, var = sys.argv[1], sys.argv[2]
    n = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 4
    assert var in SV.VARIANTS or w == "edge2"
    if w == "design":
        print(json.dumps(design(var), indent=1))
    elif w == "edge":
        design(var)
        for vth in ORDER:
            c = cal(var, vth)
            print("calibration", c["key"], c.get("mode"), c.get("vhat"), c.get("flag"), flush=True)
            wu.pool_run([wu.cls_job("S2", c, i, variant=var, idle=(c.get("mode") == "W")) for i in wu.SUB], n)
            if vth == 0.65:
                bad = nominal_ok(var)
                print("NOMINAL CHECK", var, "identical" if not bad else f"DIFFERENT on {bad}", flush=True)
                if bad:
                    print("variant FAILS the nominal check (S2.2.3); other points not run", flush=True)
                    break
    elif w == "edge2":                  # S2-D2: pick the better variant on 0.49 + 0.51 V, run 0.47 and 0.45 V for it
        def score(v):
            s = 0
            for vth in (0.49, 0.51):
                c = cal(v, vth)
                s += sum(json.load(open(wu.RAW / "S2" / f"S2_{c['key']}_v21_s{i:02d}.json")).get("valid_read") and
                         json.load(open(wu.RAW / "S2" / f"S2_{c['key']}_v21_s{i:02d}.json")).get("winner_read") ==
                         json.load(open(wu.RAW / "S2" / f"S2_{c['key']}_v21_s{i:02d}.json")).get("label") for i in wu.SUB)
            return s
        sc = {v: score(v) for v in SV.VARIANTS}
        best = sorted(sc, key=lambda v: (-sc[v], 0 if v == "R10.2-edgeA" else 1))[0]
        json.dump(dict(scores_049_051=sc, better=best, rule="S2-D2"), open(wu.SUMM / "s2_phase2_choice.json", "w"), indent=1)
        print("PHASE 2 variant", best, sc, flush=True)
        if "--choose-only" in sys.argv:
            sys.exit(0)
        for vth in ORDER2:
            c = cal(best, vth)
            print("calibration", c["key"], c.get("mode"), c.get("vhat"), c.get("flag"), flush=True)
            wu.pool_run([wu.cls_job("S2", c, i, variant=best, idle=(c.get("mode") == "W")) for i in wu.SUB], n)
    elif w == "stress":
        import wu_stress
        wu_stress.audit(var, cal(var, 0.65), f"s2_stress_{var}")
    elif w == "nominal90":
        c = cal(var, 0.65)
        wu.pool_run([wu.cls_job("S2n90", c, i, variant=var) for i in range(90) if i not in wu.SUB], n)   # S2-D1
