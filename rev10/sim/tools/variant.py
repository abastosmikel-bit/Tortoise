"""Build a netlist variant from the converted OTFT netlist by applying named edits.
Each edit is (regex, replacement). Prints how many lines each edit touched."""
import re, sys, pathlib
def make(src, dst, edits, append=""):
    txt = pathlib.Path(src).read_text()
    for pat, rep in edits:
        txt, n = re.subn(pat, rep, txt, flags=re.M)
        print(f"  [{n:2d}x] {pat[:60]}")
        if n == 0: raise SystemExit(f"edit matched nothing: {pat}")
    if append:
        i = txt.rstrip().rfind("\n.end")
        assert txt[i:].strip().lower() == ".end", "final .end not found"
        txt = txt[:i] + "\n" + append + txt[i:]
    pathlib.Path(dst).write_text(txt)
