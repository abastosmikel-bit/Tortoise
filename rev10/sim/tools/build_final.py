"""Frozen final build (netlist title "TRACE-2 FINAL (frozen)"): T10 reset/host timing + HW-trained fingers + pulsed rows + V2 lock + variant C comparator.
Optional Monte Carlo: per-instance DVTH ~ N(0, anchor*sqrt(780/(W*L))) on every TFT."""
import os, sys, re, json, numpy as np
os.environ.setdefault("FINGERS", "/home/claude/w/eval/F_hw_m4_firstpass.npy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t11 as T11, lockvar
VARIANT_C = [(r"^(X(?:81|91|101|111|121)\s+d\d\s+ap\d\s+vls\s+potft\s+)W=156\s+L=5", r"\g<1>W=468 L=15"),
             (r"^(X(?:83|93|103|113|123)\s+na\d\s+d\d\s+vdd\s+potft\s+)W=100\s+L=5", r"\g<1>W=200 L=10"),
             (r"^(X(?:82|92|102|112|122)\s+0\s+0\s+d\d\s+potft\s+)W=10\s+L=10", r"\g<1>W=20 L=20")]
def build(dst, x, prior, t_pred_us, vth="085", m=4, die_seed=None, anchor=0.050):
    T11.t11(dst, x, prior, t_pred_us, m=m, P=float(os.environ.get("PERIOD", 40)), base=f"t5L_x2_v{vth}.cir")
    lockvar.apply(dst, dst, 2)
    t = open(dst).read()
    for p, r in VARIANT_C:
        t, n = re.subn(p, r, t, flags=re.M); assert n == 5, (p, n)
    draws = {}
    if die_seed is not None:
        rng = np.random.default_rng(die_seed)
        def add(mo):
            W, L = float(mo.group(2)), float(mo.group(3)); dv = rng.normal(0, anchor * np.sqrt(780 / (W * L)))
            draws[mo.group(1).split()[0]] = dv
            return f"{mo.group(0)} DVTH={dv:.5f}"
        t = re.sub(r"^(X\S+\s+\S+\s+\S+\s+\S+\s+potft)\s+W=(\S+)\s+L=(\S+)", lambda mo: add(mo), t, flags=re.M)
        json.dump(draws, open(dst.replace(".cir", "_dvth.json"), "w"), indent=0)
    # host timing: end sampling (phib high) before the rows return high at the end of phase B (stress fix)
    SAMPLING_END = 309.0
    t, n = re.subn(r"^V_PHIB\s.*$", f"V_PHIB phib 0 PWL(0 0 {SAMPLING_END:.1f}u 0 {SAMPLING_END+1:.1f}u 3.3)", t, flags=re.M); assert n == 1
    t, n = re.subn(r"^V_PHI\s.*$", f"V_PHI phi 0 PWL(0 3.3 {SAMPLING_END:.1f}u 3.3 {SAMPLING_END+1:.1f}u 0)", t, flags=re.M); assert n == 1
    RSTR_FALL = 20.0   # host ramps rstr down over 20 us at cycle start (rails may start slightly above VDD)
    t, n = re.subn(r"^V_RSTR\s+rstr\s+0\s+PWL\(0 0\.00 ", f"V_RSTR rstr 0 PWL(0 3.3 {RSTR_FALL:.1f}u 0.00 ", t, flags=re.M); assert n == 1
    t = t.replace("TRACE-2", "TRACE-2 FINAL (frozen)", 1)
    open(dst, "w").write(t)
    return len(re.findall(r"^X\S+\s.*potft", t, re.M))
if __name__ == "__main__":
    d = np.load("/home/claude/w/repo/data/trace2_data.npz")
    idx, prior, tp = int(sys.argv[1]), sys.argv[2], float(sys.argv[3])
    vth = sys.argv[4] if len(sys.argv) > 4 else "085"; m = float(sys.argv[5]) if len(sys.argv) > 5 else 4
    seed = int(sys.argv[6]) if len(sys.argv) > 6 else None
    out = os.environ.get("OUT", f"final_s{idx}_v{vth}.cir")
    print(out, "devices:", build(out, d["X_test"][idx], prior, tp, vth, m, seed))
