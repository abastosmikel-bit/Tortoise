"""B5 mechanism probe: one run with every top-level node saved at native resolution (raw/b5_probe/<tag>.npz, LFS-free
compressed numpy is not used; we store a 0.2 us-resampled csv.gz in LFS).
Usage: python3 b5_probe.py <tag> <idx> <vth> [V1 V2] [rstb_rel] [t_end]"""
import gzip, json, re, sys
import numpy as np
import eh, common as C

OUT = eh.RAW / "b5_probe"
NODES = (C.WARM_NODES + C.TIMING + [f"row{i}" for i in range(1, 7)] + ["n1", "comp", "acom"] + [f"acol{k}" for k in range(1, 6)])


def probe(tag, idx, vth, V1=None, V2=None, rstb_rel=None, t_end=None, prior=eh.WARM):
    wd = C.workdir("eh_b5p")
    net = wd / f"{tag}.cir"
    b = eh.build(net, idx, vth=vth, V1=V1, V2=V2, rstb_rel=rstb_rel, t_end=t_end, inst=False, prior=prior)
    d, info = eh.simulate(net, tag, [f"v({n})" for n in NODES])
    net.unlink()
    t = d["time"]
    m = C.metrics(t, {n: d[f"v({n})"] for n in C.NODES}, b["tC2"], vth=vth)
    OUT.mkdir(parents=True, exist_ok=True)
    g = np.arange(0, t[-1], 0.2e-6)
    with gzip.open(OUT / f"{tag}.csv.gz", "wt") as f:
        f.write("t_us," + ",".join(NODES) + "\n")
        np.savetxt(f, np.column_stack([g * 1e6] + [np.interp(g, t, d[f"v({n})"]) for n in NODES]), fmt="%.5g", delimiter=",")
    meta = dict(tag=tag, idx=idx, vth=vth, build={k: v for k, v in b.items() if k not in ("draws", "ammeters")}, run=info, **m)
    (OUT / f"{tag}.json").write_text(json.dumps(meta, indent=1, default=float))
    return meta, t, d


if __name__ == "__main__":
    a = sys.argv[1:]
    tag, idx, vth = a[0], int(a[1]), float(a[2])
    V1 = float(a[3]) if len(a) > 3 and a[3] != "-" else None
    V2 = float(a[4]) if len(a) > 4 and a[4] != "-" else None
    rr = float(a[5]) if len(a) > 5 and a[5] != "-" else None
    te = float(a[6]) if len(a) > 6 and a[6] != "-" else None
    m, t, d = probe(tag, idx, vth, V1, V2, rr, te)
    print(json.dumps({k: m.get(k) for k in ("latched", "valid", "failure", "trip_us", "first")}, default=float))
