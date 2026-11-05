"""Model prediction for one scheme-A die from the exact SPICE DVTH draws (json written by build_final)."""
import json, sys, numpy as np
sys.path.insert(0, "/home/claude/w/eval")
from schemeA import F1, Xte, yte, SWING, TAU_FULL, VTH, sp
T1, WMIN, GAP, V2, MARGIN = 170.0, 20.0, 5.0, 2.2, 0.05
def predict(idx, jfile):
    dv = json.load(open(jfile)); x = Xte[idx]
    vov1, vov2 = 1.68 - VTH, 3.3 - V2 - VTH; r = SWING / TAU_FULL / 60
    B1 = np.zeros((6, 5)); B2 = np.zeros((6, 5))
    for k in range(5):
        for i in range(6):
            nf = F1[i, k]; d = dv.get(f"X{1+6*k+i}", 0.0)
            B1[i, k] = nf * (sp(vov1 - d) / sp(vov1)) ** 2
            B2[i, k] = nf * (sp(vov2 - d) / sp(vov2)) ** 2 * (sp(vov2) / sp(vov1)) ** 2
    delta = np.array([-dv[f"X{81+10*k}"] + dv[f"X{83+10*k}"] / 3 + 0.18 * dv[f"X{82+10*k}"] - dv[f"X{75+k}"] for k in range(5)])
    thr = SWING - MARGIN + delta
    on = WMIN + x * T1; order = np.argsort(on); V = np.zeros(5); tk = np.full(5, np.inf); tprev = 0; alive = np.ones(6, bool)
    for i in order:
        rate = r * (alive[:, None] * B1).sum(0); dt = on[i] - tprev
        hit = (V + rate * dt >= thr) & np.isinf(tk); tk[hit] = (tprev + (thr - V) / rate)[hit]
        V = V + rate * dt; tprev = on[i]; alive[i] = False
    s2 = r * B2.sum(0); c2 = WMIN + T1 + GAP + np.maximum(thr - V, 0) / s2
    tk = np.where(np.isinf(tk), c2, tk)
    o = np.argsort(tk)
    return tk, delta, o
if __name__ == "__main__":
    idx, jf = int(sys.argv[1]), sys.argv[2]
    tk, delta, o = predict(idx, jf)
    print(f"  model: comparator offsets (mV) {np.round(delta*1e3,1)} | first class {o[0]+1} at +{tk[o[0]]:.0f} us, "
          f"runner-up class {o[1]+1} +{tk[o[1]]-tk[o[0]]:.1f} us -> {'pass' if o[0]==yte[idx] and tk[o[1]]-tk[o[0]]>14 else 'fail'}")
