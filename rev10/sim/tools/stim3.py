"""Multi-cycle stimulus with a dedicated reset phase. Per cycle (t0 = cycle start):
  0 .. TR          : RESET   rows off, rstr=0 (rails+latches), rstb=0 (C_ref), phib=3.3, phi=0
  TR .. TR+10us    : PHASE B rows all active, phib=0 (sample ref), phi=3.3, rstb=3.3, rstr=0
  TR+10us          : rows -> input vector, phib=3.3, phi=0
  TR+10.5us        : rstr -> 3.3 (race starts)          [1 us edges on rstr/rstb]
  TR+tRace         : rows off (standby) until T"""
import re
def seq(levels, edge=10e-9):
    pts = [(0.0, levels[0][1])]
    for (t, v, *e) in levels[1:]:
        ed = e[0] if e else edge
        pts += [(t, pts[-1][1]), (t + ed, v)]
    return "PWL(" + " ".join(f"{t*1e6:.3f}u {v:.2f}" for t, v in pts) + ")"
def cycles(txt, vectors, TR, tRace, T):
    N = len(vectors); L = {}
    def steps(fn): return [s for k in range(N) for s in fn(k*T, k)]
    for i in range(6):
        L[f"VR{i+1}"] = seq(steps(lambda t0, k: [(t0, 3.3), (t0+TR, 1.62), (t0+TR+10e-6, 1.62 if vectors[k][i] else 3.3), (t0+TR+tRace, 3.3)]))
    L["V_RSTR"] = seq(steps(lambda t0, k: [(t0, 0.0, 1e-6), (t0+TR+10.5e-6, 3.3, 1e-6)]))
    L["V_RSTB"] = seq(steps(lambda t0, k: [(t0, 0.0, 1e-6), (t0+TR, 3.3, 1e-6)]))
    L["V_PHIB"] = seq(steps(lambda t0, k: [(t0, 3.3), (t0+TR, 0.0), (t0+TR+10e-6, 3.3)]))
    L["V_PHI"]  = seq(steps(lambda t0, k: [(t0, 0.0), (t0+TR, 3.3), (t0+TR+10e-6, 0.0)]))
    L["V_RST_COARSE"] = seq(steps(lambda t0, k: [(t0, 0.0), (t0+0.605e-6, 3.3)]))
    L["V_RST_FINE"]   = seq(steps(lambda t0, k: [(t0, 3.3), (t0+0.605e-6, 0.0)]))
    for name, w in L.items():
        txt, n = re.subn(rf"^({name}\s+\S+\s+0\s+)PWL\(.*\)\s*$", rf"\g<1>{w}", txt, flags=re.M); assert n == 1, name
    txt, n = re.subn(r"^\.tran .*$", f".tran 100n {N*T*1e6:.0f}u 0 200n", txt, flags=re.M); assert n == 1
    txt = re.sub(r"AT=\d+u", f"AT={N*T*1e6-1:.0f}u", txt)
    return txt
