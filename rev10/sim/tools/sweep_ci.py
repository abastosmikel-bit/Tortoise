"""Sweep gate-dielectric C_i (and optionally SS) in the converted classifier netlist.
Everything else = lab corner. Scores each run from the waveform, not from .measure."""
import subprocess, sys, pathlib, numpy as np
ROOT = pathlib.Path(__file__).resolve().parents[1]; C = ROOT / "circuits"
base = (C / "trace2_r4_autonomous_otft.cir").read_text()
cases = [(ci, ss) for ci in (0.033, 0.054, 0.10, 0.26, 0.50, 0.70, 0.80) for ss in (0.080,)] \
      + [(0.033, 0.200), (0.054, 0.200), (0.26, 0.120)]
cols = ['ap1','ap2','ap3','ap4','ap5','na1','na2','na3','na4','na5','winb','ref','vls','vboot','d1','d2']
lines = []
lib = []
for ci, ss in cases:
    tag = f"ci{int(round(ci*1000)):03d}_ss{int(ss*1000)}"
    lib += [f".lib {tag}", f".param MU=1.0 CI={ci}e-6 SS={ss} RCW=400 JOFF=1e-14 VTH0=1.25 LOV=2", f".endl {tag}"]
(ROOT / "models" / "ci_sweep.lib").write_text("\n".join(lib) + "\n")
print(f"{'C_i uF/cm2':>10} {'SS':>4} | {'uCi A/V2':>8} | {'1st trip':>9} {'order':>11} {'gap12':>7} | {'latched@99u':>11} {'WINB@99u':>8} | {'vboot@50u':>9} {'ap1 min':>7}")
for ci, ss in cases:
    tag = f"ci{int(round(ci*1000)):03d}_ss{int(ss*1000)}"
    net = base.replace(".lib ../models/trace2_otft.lib lab", f".lib ../models/ci_sweep.lib {tag}")
    f = C / f"sweep_{tag}.cir"; f.write_text(net)
    r = subprocess.run([sys.executable, str(ROOT/"tools"/"run_diag.py"), f.name, tag], cwd=C, capture_output=True, text=True)
    conv = "OK" if (C/f"{tag}.dat").exists() else "NO DATA"
    d = np.loadtxt(C/f"{tag}.dat"); t = d[:,0]; v = {c: d[:,2*i+1] for i,c in enumerate(cols)}
    at = lambda x, tt: x[np.searchsorted(t, tt)]
    trips = {}
    for k in range(1,6):
        na = v[f"na{k}"]; m = t > 11.2e-6          # ignore reset-edge kicks before phase C
        idx = np.where(m[1:] & (na[:-1] < 1.65) & (na[1:] >= 1.65))[0]
        if len(idx): trips[k] = t[idx[0]+1]
    order = "".join(str(k) for k in sorted(trips, key=trips.get)) or "-"
    first = f"{min(trips.values())*1e6:7.2f}us" if trips else "   none  "
    gap = (f"{(sorted(trips.values())[1]-sorted(trips.values())[0])*1e6:5.2f}us" if len(trips) > 1 else "   n/a ")
    latched = "".join(str(k) for k in range(1,6) if at(v[f"na{k}"], 99e-6) > 2.5) or "none"
    print(f"{ci:10.3f} {ss*1e3:4.0f} | {1.0*ci*1e-6:8.1e} | {first:>9} {order:>11} {gap:>7} | {latched:>11} {at(v['winb'],99e-6):8.2f} | {at(v['vboot'],50e-6):9.2f} {v['ap1'].min():7.2f}  {conv}")
