"""Per-node capacitance budget for a potft netlist (v2 capacitance rules, lab corner).
For each node: C_min (all channels off: overlaps only) and C_max (all adjacent channels on,
gate sees Ci*W*L, source/drain side sees Ci*W*L/2) plus explicit capacitors."""
import re, sys, collections
CI = 0.70e-6*1e-8   # F/um^2
LOV = 2.0
net = open(sys.argv[1]).read().splitlines()
cmin = collections.Counter(); cmax = collections.Counter(); who = collections.defaultdict(list)
for l in net:
    m = re.match(r"^X(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+potft\s+W=(\S+)\s+L=(\S+)", l)
    if m:
        name, d, g, s, W, L = m.groups(); W, L = float(W), float(L)
        ov, ch = CI*W*LOV, CI*W*L
        for n, lo, hi, role in ((g, 2*ov, 2*ov+ch, "g"), (d, ov, ov+ch/2, "d"), (s, ov, ov+ch/2, "s")):
            cmin[n] += lo; cmax[n] += hi; who[n].append(f"X{name}.{role}({W:g}/{L:g})")
        continue
    m = re.match(r"^C\S+\s+(\S+)\s+(\S+)\s+([\d.]+)([pf])", l, re.I)
    if m:
        a, b, v, u = m.groups(); c = float(v)*(1e-12 if u.lower()=="p" else 1e-15)
        for n in (a, b):
            if n != "0": cmin[n] += c; cmax[n] += c; who[n].append(f"C({v}{u})")
nodes = sys.argv[2].split(",")
for n in nodes:
    big = sorted(who[n], key=lambda s: -float(re.search(r"\((\d+\.?\d*)", s).group(1)) if "X" in s else 0)[:5]
    print(f"{n:6s} C = {cmin[n]*1e12:6.2f} .. {cmax[n]*1e12:6.2f} pF   biggest: {', '.join(big)}")
