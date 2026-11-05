"""E8 amendment: recompute every a1 estimate with the revised host sequence (phib low during reset, high from 290 us;
I_DD baseline 293-300 us): the nominal offset, all B3 dies already in b3_estimates.json and all B4 cells already in
b4_estimates.json. The superseded runs are kept in raw/b3/a1_superseded_phibhigh/."""
import json
from multiprocessing import Pool
import eh, b3_mc as B
import b4_estimates as E4

if __name__ == "__main__":
    off = json.load(open(B.OFFS_F))
    est3 = json.load(open(B.EST_F)) if B.EST_F.exists() else {}
    est4 = json.load(open(E4.F)) if E4.F.exists() else {}
    tasks = [("a1_nom", 0.65, 1.0, None)]
    tasks += [(f"a1_{k}", v["die"]["g"], 1.0, v["die"]["mc"]) for k, v in est3.items()]
    tasks += [(f"a1_g{round(v['vth']*100):03d}_m{round(v['muf']*100):03d}", v["vth"], v["muf"], None) for v in est4.values()]
    with Pool(4) as p:
        res = dict(zip([t[0] for t in tasks], p.map(B._a1, tasks)))
    old = off["a1"]
    off["a1_superseded_phibhigh"] = old
    off["a1"] = res["a1_nom"]["vth_raw"] - 0.65
    off["raw"]["a1"] = {k: res["a1_nom"][k] for k in ("vth_raw", "vsg_at_I", "I_base_uA")}
    json.dump(off, open(B.OFFS_F, "w"), indent=1, default=float)

    def entry(r):
        return dict(vth_est=(r["vth_raw"] - off["a1"]) if r.get("vth_raw") is not None else None, raw=r.get("vth_raw"),
                    vsg_at_I=r.get("vsg_at_I"), na_max=max((x for x in (r.get("na_max_during_ramp") or {}).values() if x is not None), default=None),
                    failed=r.get("failed", False))
    for k, v in est3.items():
        v["a1_superseded_phibhigh"] = v["a1"]
        v["a1"] = entry(res[f"a1_{k}"])
    for v in est4.values():
        v["a1_superseded_phibhigh"] = v["a1"]
        v["a1"] = entry(res[f"a1_g{round(v['vth']*100):03d}_m{round(v['muf']*100):03d}"])
    json.dump(est3, open(B.EST_F, "w"), indent=1, default=float)
    json.dump(est4, open(E4.F, "w"), indent=1, default=float)
    print("offset a1", old, "->", off["a1"])
    for k, v in list(est3.items()) + list(est4.items()):
        print(k, v.get("die", {}).get("g", v.get("vth")), v["a1_superseded_phibhigh"]["vth_est"], "->", v["a1"]["vth_est"])
