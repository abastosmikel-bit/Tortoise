"""Gate-dielectric stress audit: max |V(g)-V(d)| and |V(g)-V(s)| per potft instance over the transient.
Usage: python audit.py netlist.cir tag.raw [limit=3.5]"""
import re, sys, numpy as np
net, raw = sys.argv[1], sys.argv[2]; lim = float(sys.argv[3]) if len(sys.argv) > 3 else 3.5
L = open(raw, errors="ignore").read().split("\n")
nv = int([l for l in L if l.startswith("No. Variables")][0].split(":")[1]); npt = int([l for l in L if l.startswith("No. Points")][0].split(":")[1])
i0 = L.index("Variables:") + 1; names = [L[i0+k].split()[1].lower() for k in range(nv)]
j = L.index("Values:") + 1; vals = []
tok = " ".join(L[j:]).split()
# ascii raw: index, then nv values
k = 0; data = np.zeros((npt, nv))
for p in range(npt):
    k += 1  # point index
    for q in range(nv): data[p, q] = float(tok[k]); k += 1
col = {n: data[:, i] for i, n in enumerate(names)}
t = col["time"]; dt = np.diff(t, prepend=t[0])
def V(n):
    n = n.lower()
    if n == "0": return np.zeros_like(t)
    return col.get(f"v({n})", col.get(n))
rows = []
for l in open(net):
    m = re.match(r"^X(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+potft(?:seg)?\s+W=(\S+)\s+L=(\S+)", l)
    if not m: continue
    name, d, g, s, W, Lc = m.groups()
    vd, vg, vs = V(d), V(g), V(s)
    if vd is None or vg is None or vs is None: continue
    st = np.maximum(np.abs(vg - vd), np.abs(vg - vs))
    over = st > lim
    rows.append((st.max(), f"X{name}", f"g={g} d={d} s={s}", t[np.argmax(st)]*1e6, dt[over].sum()*1e6))
rows.sort(reverse=True)
n_over = sum(1 for r in rows if r[0] > lim)
print(f"{len(rows)} devices audited, {n_over} exceed {lim} V at some time. Sim length {t[-1]*1e6:.0f} us.")
for r in rows[:int(sys.argv[4]) if len(sys.argv) > 4 else 15]:
    print(f"  {r[1]:6s} max {r[0]:4.2f} V at {r[3]:7.2f} us, above limit {r[4]:7.1f} us   ({r[2]})")
