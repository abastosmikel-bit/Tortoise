"""B4: every method's |V_th| estimate on every aged cell (global corners, no mismatch; replica DVTH = 0), with the B3
design-time offsets. -> summary/b4_estimates.json (resumable). Also records the replica's mobility estimate
(a^2 relative to the nominal die), used only if the timing test (E9) asks for it."""
import json, sys
from multiprocessing import Pool
import eh, b3_mc as B, b4_aging as A, vthmeth as M

F = eh.SUMM / "b4_estimates.json"
if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    off = json.load(open(B.OFFS_F))
    res = json.load(open(F)) if F.exists() else {}
    with Pool(n) as p:
        for v, m in A.CELLS:
            k = f"{v:.2f}_{m:.2f}"
            if k in res:
                continue
            dd = dict(g=v, rep_dvth=0.0, mc=None, anchor=0, die=0)
            e = B.estimate(dd, off, p, vth=v, muf=m, prefix=f"g{round(v*100):03d}_m{round(m*100):03d}")
            res[k] = dict(vth=v, muf=m, **e, ideal=dict(vth_est=v))
            print(k, {q: e[q]["vth_est"] for q in ("rep", "a1", "a2")}, flush=True)
            json.dump(res, open(F, "w"), indent=1, default=float)
