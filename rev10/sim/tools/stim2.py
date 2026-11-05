"""Multi-cycle stimulus: N inference cycles of period T, each with its own input vector.
Per cycle (relative to cycle start t0): rstb low 0-1 us; phase B (all rows active, phib low, phi high) 1-11 us;
rows switch to the vector at 11 us; rstr (rail + latch reset) low 0-11.5 us; phase C until tC; standby to T."""
import re
def pwl(points):
    return "PWL(" + " ".join(f"{t*1e6:.3f}u {v:.2f}" for t, v in points) + ")"
def seq(levels):  # levels: list of (t_start, value) steps -> PWL with 10 ns edges
    pts = [(0.0, levels[0][1])]
    for (t, v) in levels[1:]:
        pts += [(t - 10e-9, pts[-1][1]), (t, v)]
    return pwl(pts)
def cycles(txt, vectors, T, tC):
    N = len(vectors); L = {}
    def steps(fn):
        out = []
        for k in range(N):
            t0 = k*T; out += fn(t0, k)
        return out
    for i in range(6):
        L[f"VR{i+1}"] = seq(steps(lambda t0, k: [(t0 + (0 if k else 0), 3.3), (t0+1e-6, 1.62), (t0+11e-6, 1.62 if vectors[k][i] else 3.3), (t0+tC, 3.3)])[0:] if True else None)
    L["V_RSTB"] = seq(steps(lambda t0, k: [(t0, 0.0), (t0+1e-6, 3.3)]))
    L["V_RSTR"] = seq(steps(lambda t0, k: [(t0, 0.0), (t0+11.5e-6, 3.3)]))
    L["V_PHIB"] = seq(steps(lambda t0, k: [(t0, 3.3), (t0+1e-6, 0.0), (t0+11e-6, 3.3)]))
    L["V_PHI"]  = seq(steps(lambda t0, k: [(t0, 0.0), (t0+1e-6, 3.3), (t0+11e-6, 0.0)]))
    L["V_RST_COARSE"] = seq(steps(lambda t0, k: [(t0, 0.0), (t0+0.605e-6, 3.3)]))
    L["V_RST_FINE"]   = seq(steps(lambda t0, k: [(t0, 3.3), (t0+0.605e-6, 0.0)]))
    for name, w in L.items():
        node = {"VR%d" % i: "row%d" % i for i in range(1, 7)}.get(name)
        pat = rf"^({name}\s+\S+\s+0\s+)PWL\(.*\)\s*$"
        txt, n = re.subn(pat, rf"\g<1>{w}", txt, flags=re.M); assert n == 1, name
    txt, n = re.subn(r"^\.tran .*$", f".tran 100n {N*T*1e6:.0f}u 0 200n", txt, flags=re.M); assert n == 1
    txt = re.sub(r"AT=\d+u", f"AT={N*T*1e6-1:.0f}u", txt)
    return txt
