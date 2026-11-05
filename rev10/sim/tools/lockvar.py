"""Apply lock-speed variants to a T11/T12 netlist."""
import re, sys
def apply(src, dst, level):
    t = open(src).read()
    def sub(p, r, n):
        nonlocal t; t, k = re.subn(p, r, t, flags=re.M); assert k == n, (p, k)
    if level >= 1:
        sub(r"^CWIN win 0 2p", "CWIN win 0 0.3p", 1)
        for c in range(5): sub(rf"^(X{90+10*c}\s+win\s+nb{c+1}\s+vdd\s+potft\s+)W=40", r"\g<1>W=80", 1)
    if level >= 2:
        for c in range(5): sub(rf"^(X{87+10*c}\s+0\s+0\s+nb{c+1}\s+potft\s+)W=10", r"\g<1>W=20", 1)
    if level >= 3:
        for c in range(5): sub(rf"^(X{89+10*c}\s+d{c+1}\s+lockb\s+)vdd(\s+potft)", rf"\g<1>nb{c+1}\g<2>", 1)
    open(dst, "w").write(t)
if __name__ == "__main__": apply(sys.argv[1], sys.argv[2], int(sys.argv[3]))
