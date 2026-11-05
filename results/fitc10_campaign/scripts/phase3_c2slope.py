"""C2 rail slope per Phase 3A corner (Variant 3 by default; FC10_VARIANT selects). For each corner point and each
subset sample, the slope of the first tripper's rail (or class-5 rail if none tripped) over C2 start + 300 us ..
+ 500 us, from the saved 1-us waveforms. Also the C2 overdrive 3.3 - V2 - |V_th| with V2 fixed at 2.40 V.
-> summary[/v3]/phase3A_c2slope.json"""
import glob, gzip, json
import numpy as np
import common as C
import phase3 as P

if __name__ == "__main__":
    pts = [("vth065_mu100", 0.65, C.RAW / "phase1", "s")] + [(p, vt, C.RAW / "phase3A", f"A_{p}_s") for p, vt in P.A_POINTS]
    out = {}
    for name, vt, d, pre in pts:
        sl = []
        for i in P.SUB:
            f = d / f"{pre}{i:02d}.csv.gz"
            m = json.load(open(d / f"{pre}{i:02d}.json"))
            h = gzip.open(f, "rt").readline().strip().split(","); w = np.loadtxt(f, delimiter=",", skiprows=1)
            k = m.get("first") or 5; t0 = m["tC2_us"]
            t, ap = w[:, 0], w[:, h.index(f"ap{k}")]
            sl.append((np.interp(t0 + 500, t, ap) - np.interp(t0 + 300, t, ap)) / 200 * 1e3)   # mV/us
        out[name] = dict(vth=vt, c2_overdrive_V=round(3.3 - 2.40 - vt, 3) if name.startswith("vth") else 0.25,
                         c2_slope_mV_per_us_median=round(float(np.median(sl)), 4), min=round(float(min(sl)), 4), max=round(float(max(sl)), 4), n=len(sl))
    (C.SUMM / "phase3A_c2slope.json").write_text(json.dumps(out, indent=1))
    for k, v in out.items():
        print(k, v)
