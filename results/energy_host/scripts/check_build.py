"""Check: eh.build (no host option, no instrumentation) == fitc10 common.build(variant=3), byte for byte, for the nominal
die, a re-trimmed 0.85 V corner (lib line normalised: eh corner lib vs fitc10_sweep.lib, same parameter values) and a
pelgrom_vth MC die. Also checks that the eh row-PWL generator reproduces build_A's rows when called with defaults.
-> summary/check_build.json"""
import json, re
import eh, common as C

wd = C.workdir("eh_check")
res = []
cases = [("nominal", dict(), dict()),
         ("retrim085", dict(corner=("fitc10_sweep.lib", "fc10_vth085"), levels_vth=0.85), dict(vth=0.85, V1=1.62, V2=2.20)),
         ("mc_pv35_d3", dict(mc=dict(seed=35003, s_vth=0.035, s_mu=0.1, s_rc=0.2, scale="pelgrom_vth")),
          dict(mc=dict(seed=35003, s_vth=0.035, s_mu=0.1, s_rc=0.2, scale="pelgrom_vth")))]
for name, ca, ea in cases:
    for idx in (81, 31):
        a, b = wd / f"c_{name}_{idx}.cir", wd / f"e_{name}_{idx}.cir"
        C.build(a, idx, eh.WARM, 3, **ca)
        eh.build(b, idx, inst=False, **ea)
        ta, tb = a.read_text(), b.read_text()
        norm = lambda s: re.sub(r"^\.lib .*$", ".lib <corner>", s, flags=re.M)
        same = ta == tb
        same_norm = norm(ta) == norm(tb)
        # rows via eh.row_pwl with defaults (rows_off=None, cal_k=1) must equal build_A's rows
        bb = wd / f"r_{name}_{idx}.cir"
        eh.build(bb, idx, inst=False, rows_off=None, cal_k=1.0000001, **ea)  # forces the eh PWL path (tiny shift)
        rows_same = all(abs(float(x) - float(y)) < 1e-3 for x, y in zip(
            re.findall(r"[-\d.]+", " ".join(re.findall(r"^VR\d.*$", tb, re.M))),
            re.findall(r"[-\d.]+", " ".join(re.findall(r"^VR\d.*$", bb.read_text(), re.M)))))
        res.append(dict(case=name, idx=idx, identical=same, identical_except_lib_line=same_norm, eh_row_pwl_matches=rows_same))
        print(res[-1])
json.dump(res, open(eh.SUMM / "check_build.json", "w"), indent=1)
assert all(r["identical_except_lib_line"] and r["eh_row_pwl_matches"] for r in res)
