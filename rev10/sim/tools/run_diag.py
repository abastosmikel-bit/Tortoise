"""Run a top-level classifier netlist with extra measurements, without modifying it.
Usage: python run_diag.py <netlist.cir> [tag] [extra .param/.lib override lines...]"""
import re, sys, subprocess, pathlib
src = pathlib.Path(sys.argv[1]); tag = sys.argv[2] if len(sys.argv) > 2 else "diag"
extra = sys.argv[3:]
import os
NODES = ["ap1","ap2","ap3","ap4","ap5","na1","na2","na3","na4","na5","ref","vls","vboot","d1","d2","d3","d4","d5","nb1","nb2","nb3","nb4","nb5"]
_t = pathlib.Path(sys.argv[1]).read_text()
TOP = sorted({n.lower() for l in _t.splitlines() if re.match(r"^[XxMmCcRrVv]", l)
               for n in l.split()[1:4] if re.match(r"^[a-z_][a-z0-9_]*$", n.lower()) and n.lower() not in ("potft","pwl","dc")})
NODES += [n for n in os.environ.get("EXTRA_NODES","").split() if n]
NODES += [n for n in ("winb","win","tripvdd","lockb") if re.search(r"\s%s(\s|$)" % n, _t, re.M)]
if os.environ.get("RELAX"): extra.append(".options RELTOL=1e-3 ABSTOL=1e-12 VNTOL=1e-6 CHGTOL=1e-14 ITL4=100 METHOD=GEAR MAXORD=2")
txt = src.read_text()
txt = re.sub(r"(?is)^\.control.*?^\.endc\s*$", "", txt, flags=re.M)
meas = []
for k in range(1, 6):
    meas += [f".measure tran t_trip{k}x WHEN v(na{k})=1.65 RISE=1",
             f".measure tran ap{k}_at54 FIND v(ap{k}) AT=53.0u",
             f".measure tran na{k}_max MAX v(na{k}) FROM=11u TO=99u",
             f".measure tran d{k}_min MIN v(d{k}) FROM=11u TO=99u"]
meas += [".measure tran t_winb_fall WHEN v(winb)=2.4 FALL=1",
         ".measure tran vboot_min MIN v(vboot) FROM=0 TO=99u",
         ".measure tran ap1_at11 FIND v(ap1) AT=10.99u",
         ".measure tran ref_at11 FIND v(ref) AT=10.99u",
         ".measure tran vls_at30 FIND v(vls) AT=30u",
         ".measure tran i_vdd_avg AVG i(vdd) FROM=11u TO=65u"]
ctl = ["\n".join(extra), "\n".join(meas),
       ".control", "set filetype=ascii", "run",
       "wrdata " + tag + ".dat " + " ".join(f"v({n})" for n in NODES),
       *(["write " + tag + ".raw " + " ".join(f"v({n})" for n in TOP)] if os.environ.get("AUDIT") else []), "quit", ".endc"]
i = txt.rstrip().rfind("\n.end"); assert txt[i:].strip().lower()==".end"
txt = txt[:i] + "\n" + "\n".join(ctl) + txt[i:]
out = src.with_name(f"_{tag}.cir"); out.write_text(txt)
src.with_name(f"{tag}.cols").write_text(" ".join(NODES))
r = subprocess.run(["ngspice", "-n", out.name], cwd=out.parent, capture_output=True, text=True, timeout=3000, stdin=subprocess.DEVNULL)
log = r.stdout + r.stderr
out.with_suffix(".log").write_text(log)
for line in log.splitlines():
    if re.match(r"^\s*[a-z_0-9]+\s+=", line, re.I) or re.search(r"error|warning|abort|singular|too small|failed", line, re.I):
        print(line.rstrip())
m = re.search(r"Total analysis time.*", log); print(m.group(0) if m else "NO COMPLETION LINE")
