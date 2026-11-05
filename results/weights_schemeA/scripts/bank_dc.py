"""Crossbar-bank current vs V_th offset, from the device model itself (ngspice DC, potftseg in its _mc form with KMU=KRC=1).
Source at VDD 3.3 V, gate at the row level of C1 (V1) or C2 (V2), drain (the rail) at 0.9 / 1.3 / 1.7 V.
Banks of 1 and 30 fingers (W = 10 and 300 um, L = 54 um). Corners: nominal fitc10 (0.65 V) and the re-trimmed
|V_th| points 0.55-0.95 V (V1 = 3.3-|V_th|-0.83, V2 = 3.3-|V_th|-0.25).
g(d) = I(DVTH=d)/I(DVTH=0) is the factor the surrogate applies to a bank's current (W4.3/W5).
-> summary/bank_dc.json"""
import json, re, subprocess
import numpy as np
import wcommon as W

DV = np.round(np.arange(-0.20, 0.2001, 0.01), 3)
VD = (0.9, 1.3, 1.7)


def run(vth, lib, sec):
    wd = W.C.workdir("wsA_bankdc_v3")
    V1, V2 = round(3.3 - vth - 0.83, 3), round(3.3 - vth - 0.25, 3)
    lines = ["* bank dc", f".lib ../models/{lib} {sec}", ".include ../models/trace2_otft_seg_mc.sub",
             "VDD vdd 0 3.3", f"VG1 g1 0 {V1}", f"VG2 g2 0 {V2}"]
    names = []
    for gi, g in ((1, "g1"), (2, "g2")):
        for vd in VD:
            for nf in (1, 30):
                for j, d in enumerate(DV):
                    nm = f"{g}_{int(vd*10)}_{nf}_{j}"
                    lines.append(f"Vm_{nm} vdd s_{nm} 0")
                    lines.append(f"Vd_{nm} d_{nm} 0 {vd}")
                    lines.append(f"X_{nm} d_{nm} {g} s_{nm} potftseg W={10*nf} L=54 DVTH={d:.4f} KMU=1 KRC=1")
                    names.append((gi, vd, nf, j, nm))
    lines += [".options RELTOL=1e-6 ABSTOL=1e-15", ".control", "op"]
    lines += [f"print i(Vm_{nm})" for *_, nm in names]
    lines += ["quit", ".endc", ".end"]
    f = wd / f"bank_{sec}.cir"
    f.write_text("\n".join(lines) + "\n")
    r = subprocess.run(["ngspice", "-b", f.name], cwd=wd, capture_output=True, text=True)
    vals = {m.group(1).lower(): float(m.group(2)) for m in re.finditer(r"i\(vm_(\S+)\)\s*=\s*(\S+)", r.stdout, re.I)}
    out = {}
    for gi, vd, nf, j, nm in names:
        out.setdefault(f"g{gi}", {}).setdefault(str(vd), {}).setdefault(str(nf), [None] * len(DV))[j] = vals[nm.lower()]
    res = {}
    for g, byvd in out.items():
        res[g] = {}
        for vd, bynf in byvd.items():
            res[g][vd] = {}
            for nf, I in bynf.items():
                I = np.array(I); i0 = I[len(DV) // 2]
                res[g][vd][nf] = dict(I0_A=float(i0), I_per_finger_A=float(i0) / int(nf), factor=[round(float(x), 6) for x in I / i0])
    return dict(vth=vth, V1=V1, V2=V2, dvth=DV.tolist(), data=res)


if __name__ == "__main__":
    pts = [(0.65, "fitc10.lib", "fitc10")] + [(v, "fitc10_sweep.lib", f"fc10_vth{int(round(v*100)):03d}") for v in (0.55, 0.75, 0.85, 0.95)]
    res = {f"{v:.2f}": run(v, lib, sec) for v, lib, sec in pts}
    (W.SUMM / "bank_dc.json").write_text(json.dumps(res, indent=1))
    for k, r in res.items():
        for g in ("g1", "g2"):
            d = r["data"][g]
            f30 = np.array(d["1.3"]["30"]["factor"]); f1 = np.array(d["1.3"]["1"]["factor"]); f30b = np.array(d["0.9"]["30"]["factor"])
            i = list(np.round(DV, 3)).index(0.03)
            print(f"|Vth| {k} {g}: I/finger {d['1.3']['30']['I_per_finger_A']:.3e} A (1-finger bank {d['1.3']['1']['I_per_finger_A']:.3e}); "
                  f"g(+30 mV) = {f30[i]:.4f} (1 finger {f1[i]:.4f}; rail 0.9 V {f30b[i]:.4f}); dg/dV at 0 = {(f30[len(DV)//2+1]-f30[len(DV)//2-1])/0.02:.2f} /V")
