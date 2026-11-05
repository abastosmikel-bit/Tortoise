"""B1.4: standby power (DECISIONS E2). Start from the end state of a B1 classification run (one per winning class, plus
one invalid run if any), rows ramp V2 -> 3.3 V over 0.2 us at t = 1 us, every other line at its idle DC level
(rstr 3.3, rstb 3.3, phib 3.3, phi 0, VDD 3.3). Free timestep (no 100 ns cap: this is a slow settling run), to 1e5 s (the < 1 % per decade rule is met only between 1e4 and 1e5 s; DECISIONS E2).
Instrumented as in E1. Steady state: total power at the end vs one decade earlier.
Usage: python3 b1_standby.py [tags...]   -> raw/b1_standby/<tag>.json, summary/b1_standby.json"""
import glob, json, re, sys
import numpy as np
import eh, common as C

OUT = eh.RAW / "b1_standby"
T_STOP = 1.0e5


def _net(m, tag, stage, ic_state, rows_ramp):
    wd = C.workdir("eh_sb")
    net = wd / f"sb{stage}_{tag}.cir"
    b = eh.build(net, m["idx"], inst=True)
    t = net.read_text()
    V2 = b["V2"]
    for i in range(1, 7):
        src = f"PWL(0 {V2} 1u {V2} 1.2u 3.3)" if rows_ramp else "DC 3.3"
        t, n = re.subn(rf"^(VR{i}\s+row{i}\s+0\s+).*$", rf"\g<1>{src}", t, flags=re.M); assert n == 1
    for nm, node, lev in (("V_RSTR", "rstr", 3.3), ("V_RSTB", "rstb", 3.3), ("V_PHIB", "phib", 3.3), ("V_PHI", "phi", 0.0)):
        t, n = re.subn(rf"^{nm}\s.*$", f"{nm} {node} 0 DC {lev}", t, flags=re.M); assert n == 1
    ic = ".ic " + " ".join(f"v({k})={ic_state[k]:.6f}" for k in ic_state) + " v(vboot)=0"
    t, n = re.subn(r"^\.ic .*$", ic, t, flags=re.M); assert n == 1
    tran = ".tran 100n 2m 0 100n" if stage == "A" else f".tran 1u {T_STOP:g} 0 {T_STOP/200:g}"
    t, n = re.subn(r"^\.tran .*$", tran, t, flags=re.M); assert n == 1
    t = re.sub(r"^\.measure .*$", "", t, flags=re.M)
    net.write_text(t)
    return net, b


def standby(tag, src_json):
    """Stage A: 0-2 ms, 100 ns step (rows return to 3.3 V at 1 us). Stage B: rows DC 3.3 V, .ic = stage A end state
    (all saved top-level nodes), free step to T_STOP. Times in stage B are reported from the start of idling (+2 ms)."""
    m = json.load(open(src_json))
    es = {k: m["end_state"][k] for k in C.WARM_NODES}
    res = dict(tag=tag, src=str(src_json), idx=m["idx"], winner_src=m.get("winner"), latched_src=m.get("latched"))
    netA, b = _net(m, tag, "A", es, True)
    vecs = eh.vec_list(b["ammeters"]) + ["v(n1)", "v(comp)", "v(acom)"] + [f"v(acol{k})" for k in range(1, 6)]
    dA, infoA = eh.simulate(netA, f"sbA_{tag}", vecs)
    netA.unlink()
    res["runA"] = infoA
    if dA is None:
        return res
    ptA = sum(-dA[f"v({node})"] * dA[f"i({s.lower()})"] for s, node in eh.SOURCES.items())
    res["E_stageA_2ms_nJ"] = float(np.trapezoid(ptA, dA["time"])) * 1e9
    res["P_total_uW_stageA_end"] = float(ptA[-1]) * 1e6
    esB = {k: float(dA[f"v({k})"][-1]) for k in C.WARM_NODES + ["n1", "comp", "acom"] + [f"acol{k}" for k in range(1, 6)]}
    netB, b = _net(m, tag, "B", esB, False)
    d, info = eh.simulate(netB, f"sbB_{tag}", eh.vec_list(b["ammeters"]))
    netB.unlink()
    res["run"] = info
    if d is not None:
        tt = d["time"]
        p_src = {s: -d[f"v({node})"] * d[f"i({s.lower()})"] for s, node in eh.SOURCES.items()}
        ptot = sum(p_src.values())
        at = lambda y, x: float(np.interp(x, tt, y))
        res["t_end_s"] = float(tt[-1])
        res["P_total_uW_at"] = {f"{x:g}s": at(ptot, x) * 1e6 for x in (1e-4, 1e-3, 1e-2, 0.1, 1, 10, 100, 1e3, 1e4, 1e5, 1e6) if x <= tt[-1]}
        res["P_source_uW_end"] = {s: at(p, tt[-1]) * 1e6 for s, p in p_src.items()}
        res["P_block_uW_end"] = {f"{p_}:{b_}": at(d[f"v({p_})"] * d[f"i(vam_{p_}_{b_})"], tt[-1]) * 1e6 for p_, b_ in b["ammeters"]}
        res["P_block_uW_start"] = {f"{p_}:{b_}": at(d[f"v({p_})"] * d[f"i(vam_{p_}_{b_})"], 1e-4) * 1e6 for p_, b_ in b["ammeters"]}
        p_end, p_dec = at(ptot, tt[-1]), at(ptot, tt[-1] / 10)
        res["steady_rel_change_last_decade"] = abs(p_end - p_dec) / abs(p_end)
        res["steady"] = res["steady_rel_change_last_decade"] < 0.01
        res["node_end"] = {n: at(d[f"v({n})"], tt[-1]) for n in C.WARM_NODES}
        res["node_start"] = es
        res["E_stageB_nJ"] = float(np.trapezoid(ptot, tt)) * 1e9
        lg = np.logspace(-6, np.log10(tt[-1]), 121)
        res["trace"] = dict(t_s=lg.tolist(), P_total_uW=(np.interp(lg, tt, ptot) * 1e6).tolist(),
                            **{f"v_{n}": np.interp(lg, tt, d[f"v({n})"]).tolist() for n in ("ap1", "ap5", "ref", "vls", "na1", "na5", "nb1", "win")})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{tag}.json").write_text(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    for tag in sys.argv[1:]:
        f = OUT / f"{tag}.json"
        if f.exists() and json.load(open(f)).get("t_end_s", 0) >= 0.99 * T_STOP:
            print(tag, "done", flush=True)
            continue
        r = standby(tag, eh.RAW / f"b1_energy/{tag}.json")
        print(tag, r["run"], r.get("P_total_uW_at"), r.get("steady"), flush=True)
