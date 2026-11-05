"""Study 2 circuit variants (DECISIONS S2): sizing-only changes of existing Tortoise v1.0 devices, applied to the final
netlist text by wu's simulate wrapper. Importing this module registers the variants in wu.VARIANTS.
Every variant keeps the 134 TFT instances of Tortoise v1.0 (no device added or removed)."""
import re
import wu


class Resize:
    def __init__(self, name, changes, note):
        self.name, self.changes, self.note = name, changes, note     # changes: {instance: dict(W=..., L=...)}

    def apply(self, txt, ctx):
        for inst, wl in self.changes.items():
            def sub(m):
                s = m.group(0)
                for p, v in wl.items():
                    s, n = re.subn(rf"\b{p}=\S+", f"{p}={v:g}", s, count=1)
                    assert n == 1, (inst, p)
                return s
            txt, n = re.subn(rf"^{re.escape(inst)}\s+\S+\s+\S+\s+\S+\s+potft(?:seg)?\s+W=\S+\s+L=\S+", sub, txt, flags=re.M)
            assert n == 1, (self.name, inst, n)
        return txt, []

    def n_tft(self, txt):
        return sum(1 for l in txt.splitlines() if re.match(r"^X\S+\s.*potft", l))


PK = ["X90", "X100", "X110", "X120", "X130"]          # P_k: wired-OR pull-ups of win (gate nb_k), 80/5 um
CANDIDATES = {
    "dev-X80L60": Resize("dev-X80L60", {"X80": dict(L=60)}, "idle pull-down of win X80: L 120 -> 60 um (2x stronger)"),
    "dev-X80L20": Resize("dev-X80L20", {"X80": dict(L=20)}, "idle pull-down of win X80: L 120 -> 20 um (6x, base-design length)"),
    "dev-PkL10": Resize("dev-PkL10", {p: dict(L=10) for p in PK}, "P_k pull-ups of win: L 5 -> 10 um (half the leakage)"),
    "dev-XI2L60": Resize("dev-XI2L60", {"XI2": dict(L=60)}, "inverter load XI2: L 30 -> 60 um (lockb stays high to a higher win)"),
    # added to the screen after the first 0.45 V runs showed slow latch regeneration (development, PROGRESS item 6)
    "dev-X80L20-X83W400": Resize("dev-X80L20-X83W400", {"X80": dict(L=20), **{f"X{83 + 10 * c}": dict(W=400) for c in range(5)}},
                                 "X80 L 120 -> 20 um and trip drivers X83/93/103/113/123 W 200 -> 400 um"),
}
for _k, _v in CANDIDATES.items():
    wu.VARIANTS[_k] = _v

# ---- Study 2 variants (DECISIONS S2.1), candidates; Tortoise v1.0 is unchanged
VARIANTS = {
    "R10.2-edgeA": Resize("R10.2-edgeA", {"X80": dict(L=20)}, "X80 (idle pull-down of win) L 120 -> 20 um, W 5 um"),
    "R10.2-edgeB": Resize("R10.2-edgeB", {p: dict(L=10) for p in PK}, "P_k pull-ups X90/X100/X110/X120/X130 L 5 -> 10 um, W 80 um"),
}
for _k, _v in VARIANTS.items():
    wu.VARIANTS[_k] = _v
