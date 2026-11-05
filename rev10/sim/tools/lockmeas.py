import sys; sys.path.insert(0, '../tools'); from score import score, load
import numpy as np
def meas(tag, w, expect, vth=0.85):
    r = score(tag, t_on=313e-6, expect=expect, t_off=5000e-6, quiet=True)
    v, t = load(tag); m = t > 313e-6; on = 3.3 - vth
    def cross(n, lev, up=True):
        x = v[n]; c = (x[:-1] < lev) & (x[1:] >= lev) if up else (x[:-1] > lev) & (x[1:] <= lev)
        i = np.where(m[1:] & c)[0]; return t[i[0]+1]*1e6 if len(i) else float('nan')
    t0 = cross(f"na{w}", 1.65); tl = cross("lockb", on, False)
    print(f"{tag:14s} winner na>1.65 @ {t0:7.1f} us | lockb<{on:.2f} (M89 on) @ {tl:7.1f} us | lock chain {tl-t0:5.1f} us | "
          f"latched {r['latched']} runner-up na end {r['ro']:.2f} -> {'VALID' if r['valid'] else 'FAIL'}")
if __name__ == "__main__": meas(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
