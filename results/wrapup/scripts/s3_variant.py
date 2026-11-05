"""Study 3 circuit variant R10.2-bias (DECISIONS S3): a 7th crossbar row `row7`, driven by the host, with one bank per
class (potftseg, W = 10 um x Fb[k], L = 54 um, drain ap_k, gate row7, source vdd; empty banks removed). Optionally a new
6 x 5 input matrix F6 (the crossbar banks X1-X30 are rewritten textually; same instance names and geometry rule as
the frozen builder: bank (i, k) = X{6k + i + 1}, W = 10 um x F, L = 54 um).

row7 stimulus (S3.1):
  classification, mode G : PWL 0 -> 3.3 V over 0-10 us (with the other rows), 3.3 V, then V1 from t0 for
                           WMIN + XB * T1 * k (0.2 us edges), back to 3.3 V; nothing in calibration (ref sampling) or C2
  classification, mode W : the same without the power-up ramp
  calibration session    : row7 held at 3.3 V (off) in a1 and in both cross-check races (after the power-up ramp)
  idle                   : as the other rows (mode G ramp to 0 V; mode W DC 3.3 V)
Mismatch (S3.4): size-scaled V_th only, draws paired with the Tortoise v1.0 dies (host_v2 C4 / fitc10 3B-V): the z-score of
every instance that exists in Tortoise v1.0 is replayed from the same seed over the Tortoise v1.0 instance list in sorted-name
order (as common.apply_mc draws it); new instances (bias banks, crossbar banks empty in Tortoise v1.0) get z from
default_rng(seed + 9_000_000) in a fixed order. DVTH = z * s_vth * sqrt(780 / (W L)) with each instance's own W L."""
import re
import numpy as np
import wu, eh, hv2

XB = 0.5                  # bias pulse: WMIN + XB * T1 * k  (105 us at k = 1)
REV101_GEO = None


def _rev101_geometry():
    """{instance: (W, L)} of the Tortoise v1.0 die (the canonical netlist), the instance set the C4 dies were drawn over."""
    global REV101_GEO
    if REV101_GEO is None:
        t = (wu.REPO / "docs/rev10_1_nominal.cir").read_text()
        REV101_GEO = {m.group(1): (float(m.group(2)), float(m.group(3))) for m in
                      re.finditer(r"^(X\S+)\s+\S+\s+\S+\s+\S+\s+potft(?:seg)?\s+W=(\S+)\s+L=(\S+)", t, re.M)}
    return REV101_GEO


def paired_draws(geo, seed, s_vth, s_mu=0.10, s_rc=0.20):
    old = _rev101_geometry()
    rng = np.random.default_rng(seed)
    z = {}
    for nm in sorted(old):
        f = float(np.sqrt(780.0 / (old[nm][0] * old[nm][1])))
        dv = float(rng.normal(0, s_vth * f)); rng.normal(1, s_mu * f); rng.normal(0, s_rc * f)
        z[nm] = dv / (s_vth * f)
    new = sorted(n for n in geo if n not in z)
    rng2 = np.random.default_rng(seed + 9_000_000)
    extra = {nm: float(rng2.standard_normal()) for nm in [f"X{j}" for j in range(1, 31)] + [f"XB{k}" for k in range(1, 6)]}
    out = {}
    for nm in geo:
        f = float(np.sqrt(780.0 / (geo[nm][0] * geo[nm][1])))
        zz = z[nm] if nm in z else extra[nm]
        out[nm] = dict(DVTH=float(zz * s_vth * f), z=zz, paired=nm in z)
    return out, new


def row7_pwl(txt, ctx, xb=XB):
    typ = wu.netlist_type(txt)
    if typ == "idleW":
        return "DC 3.3"
    if typ == "idleG":
        return re.search(r"^VR1\s+\S+\s+0\s+(PWL\(.*\))$", txt, re.M).group(1)
    if typ == "a1":
        vr1 = re.search(r"^VR1\s+\S+\s+0\s+(PWL\(.*\))$", txt, re.M).group(1)
        return "PWL(0 0 10u 3.3)" if vr1.startswith("PWL(0 0 10u") else "DC 3.3"
    cold, t0, V1, tC2, k = wu.cls_row_timing(txt)
    pre = "0 0 10u 3.3" if cold else "0 3.3"
    if ctx.get("in_cal"):
        return f"PWL({pre})" if cold else "DC 3.3"
    w = hv2.WMIN + xb * hv2.T1_BASE * k
    assert t0 + w + 0.2 < tC2, (t0, w, tC2)
    return f"PWL({pre} {t0:.2f}u 3.3 {t0 + 0.2:.2f}u {V1} {t0 + w:.2f}u {V1} {t0 + w + 0.2:.2f}u 3.3)"


class BiasRow:
    def __init__(self, name, Fb, F6=None, xb=XB):
        self.name, self.Fb, self.xb = name, [int(v) for v in Fb], xb
        self.F6 = None if F6 is None else np.asarray(F6, int)

    def apply(self, txt, ctx):
        if self.F6 is not None:
            lines = txt.split("\n")
            pat = re.compile(r"^X([0-9]+)\s+ap[1-5]\s+row[1-6]\s+vdd\s+potftseg\s")
            idx = [i for i, l in enumerate(lines) if pat.match(l) and 1 <= int(pat.match(l).group(1)) <= 30]
            new = [f"X{6 * k + i + 1} ap{k + 1} row{i + 1} vdd potftseg W={10 * self.F6[i, k]} L=54"
                   for k in range(5) for i in range(6) if self.F6[i, k] > 0]
            lines = lines[:idx[0]] + new + [l for j, l in enumerate(lines) if j > idx[0] and j not in set(idx)]
            txt = "\n".join(lines)
        banks = [f"XB{k + 1} ap{k + 1} row7 vdd potftseg W={10 * f} L=54   $ R10.2-bias: bias bank, class {k + 1}"
                 for k, f in enumerate(self.Fb) if f > 0]
        src = f"VR7  row7 0  {row7_pwl(txt, ctx, self.xb)}   $ R10.2-bias: bias row (host-driven)"
        txt, n = re.subn(r"^(VR6\s+\S+\s+0\s+.*)$", lambda m: m.group(1) + "\n" + src, txt, count=1, flags=re.M)
        assert n == 1
        m = re.search(r"^X\S+\s+ap1\s+row\d\s+vdd\s+potftseg.*$", txt, re.M)
        txt = txt[:m.start()] + "\n".join(banks) + "\n" + txt[m.start():]
        die = ctx.get("die")
        if die:
            geo = {mm.group(1): (float(mm.group(2)), float(mm.group(3))) for mm in
                   re.finditer(r"^(X\S+)\s+\S+\s+\S+\s+\S+\s+potft(?:seg)?\s+W=(\S+)\s+L=(\S+)", txt, re.M)}
            dr, _ = paired_draws(geo, die["seed"], die["s_vth"])
            txt, n = re.subn(r"^(X\S+)\s+\S+\s+\S+\s+\S+\s+potft(?:seg)?\s+W=\S+\s+L=\S+",
                             lambda mm: f"{mm.group(0)} DVTH={dr[mm.group(1)]['DVTH']:.5f} KMU=1.00000 KRC=1.00000", txt, flags=re.M)
            assert n == len(geo)
            txt = txt.replace(".include ../models/trace2_otft_v2.sub", ".include ../models/trace2_otft_v2_mc.sub")
            txt = txt.replace(".include ../models/trace2_otft_seg.sub", ".include ../models/trace2_otft_seg_mc.sub")
        return txt, ["v(row7)", "i(vr7)"]

    def n_banks(self):
        return int((self.F6 > 0).sum() if self.F6 is not None else 21) + sum(f > 0 for f in self.Fb)

    def n_tft(self):
        return 113 + self.n_banks()


def register(name, Fb, F6=None, xb=XB):
    v = BiasRow(name, Fb, F6, xb)
    wu.VARIANTS[name] = v
    return v


def use_row7_energy():
    """Count the bias-row driver in the per-source energy (hv21.source_energy iterates eh.SOURCES)."""
    eh.SOURCES["VR7"] = "row7"
