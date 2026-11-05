"""T10 = T9 (sampling during 300 us reset, nb pull-up latch reset) + host timing lines + SEQ8 removed.
Warm start from the recorded end state of a previous run (tag of that run)."""
import re, sys, numpy as np
sys.path.insert(0, 'tools'); sys.path.insert(0, '../tools')
import t8 as T8
from score import load
def t10(src, dst, x, prior=None, T1=300e-6, tC=1200e-6):
    T8.SAMPLE_IN_RESET = True
    T8.t8(src, dst, x, T1=T1, tC=tC, warm=False)
    t = open(dst).read()
    t = re.sub(r"^(X13[3-9]|X140|CA |CB |V_RST_COARSE|V_RST_FINE).*$", r"* removed (SEQ8 replaced by host timing): \g<0>", t, flags=re.M)
    if prior:
        v, tt = load(prior); k = len(tt) - 1
        nodes = [f"ap{i}" for i in range(1, 6)] + [f"na{i}" for i in range(1, 6)] + [f"nb{i}" for i in range(1, 6)] \
              + [f"d{i}" for i in range(1, 6)] + ["ref", "win", "lockb", "vls"]
        ic = ".ic " + " ".join(f"v({n})={v[n][k]:.3f}" for n in nodes if n in v)
        i = t.index('.ic '); j = t.index('\n', t.index('v(win)=', i)); t = t[:i] + ic + " v(vboot)=0" + t[j:]
    open(dst, "w").write(t)
    return len(re.findall(r"^X\S+\s.*potft", t, re.M))
if __name__ == "__main__":
    src, dst, xs = sys.argv[1:4]; prior = sys.argv[4] if len(sys.argv) > 4 else None
    print("devices:", t10(src, dst, [int(c) for c in xs], prior))
