"""Generate T4 (no negative bias) variants with given sizes. p: dict of W (L fixed per device)."""
import re, sys
sys.path.insert(0, '../tools'); from stim import rows
BASE = open('t4s.cir').read()
DEF = dict(M65=790, M82=10, M82L=10, M83=100, M84=10, M84L=20, M87=10, PK=40, XI1=40, XI2=10, M89=20, M80=5, M80L=20)
def gen(p, x, name, tC=600e-6, tsim=700e-6):
    q = dict(DEF); q.update(p); t = BASE
    def sub(pat, rep, n=None):
        nonlocal t; t, k = re.subn(pat, rep, t, flags=re.M)
        assert k == (n if n else k) and k > 0, pat
    sub(r"^(X65\s+vls\s+n1\s+vdd\s+potft\s+)W=\d+", rf"\g<1>W={q['M65']}", 1)
    for c in range(1, 6):
        b = 81 + 10*(c-1)
        sub(rf"^(X{b+1}\s+0\s+0\s+d{c}\s+potft\s+)W=\d+\s+L=\d+", rf"\g<1>W={q['M82']} L={q['M82L']}", 1)
        sub(rf"^(X{b+2}\s+na{c}\s+d{c}\s+vdd\s+potft\s+)W=\d+", rf"\g<1>W={q['M83']}", 1)
        sub(rf"^(X{b+3}\s+0\s+0\s+na{c}\s+potft\s+)W=\d+\s+L=\d+", rf"\g<1>W={q['M84']} L={q['M84L']}", 1)
        sub(rf"^(X{b+6}\s+0\s+0\s+nb{c}\s+potft\s+)W=\d+", rf"\g<1>W={q['M87']}", 1)
        sub(rf"^(X{b+8}\s+d{c}\s+lockb\s+vdd\s+potft\s+)W=\d+", rf"\g<1>W={q['M89']}", 1)
        sub(rf"^(X{b+9}\s+win\s+nb{c}\s+vdd\s+potft\s+)W=\d+", rf"\g<1>W={q['PK']}", 1)
    sub(r"^(XI1\s+lockb\s+win\s+vdd\s+potft\s+)W=\d+", rf"\g<1>W={q['XI1']}", 1)
    sub(r"^(XI2\s+0\s+0\s+lockb\s+potft\s+)W=\d+", rf"\g<1>W={q['XI2']}", 1)
    sub(r"^(X80\s+0\s+0\s+win\s+potft\s+)W=\d+\s+L=\d+", rf"\g<1>W={q['M80']} L={q['M80L']}", 1)
    open(name, 'w').write(rows(t, x, tC, tsim))
