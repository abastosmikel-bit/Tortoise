"""Tortoise T6 illustrative layout SVG. Units: 1 user unit = 1 um. Sizes from the T6 netlist."""
import re, math
import sys
NET = sys.argv[1] if len(sys.argv) > 1 else "t6L_x2_v115.cir"
CI_FF_UM2 = 7.0                      # 0.70 uF/cm2
dev = {}
for l in open(NET):
    m = re.match(r"^X(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+potft\s+W=(\S+)\s+L=(\S+)", l)
    if m: dev[m.group(1)] = dict(d=m.group(2), g=m.group(3), s=m.group(4), W=float(m.group(5)), L=float(m.group(6)))
caps = {m.group(1): float(m.group(2)) for m in re.finditer(r"^(C\S+)\s+\S+\s+\S+\s+([\d.]+)p", open(NET).read(), re.M)}
assert len(dev) == 146, len(dev)

L_AL, L_DN, L_AU, L_VIA, L_TX, L_DECO, L_TIP = [], [], [], [], [], [], []
def r(layer, x, y, w, h, cls, rx=1.2, extra=""):
    layer.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" class="{cls}" {extra}/>')
def path(layer, pts, cls, w):
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    layer.append(f'<path d="{d}" class="{cls}" stroke-width="{w}"/>')
def via(x, y): L_VIA.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.2" class="via"/>')
def txt(x, y, s, cls="t", anchor="start"): L_TX.append(f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" text-anchor="{anchor}">{s}</text>')
def flag(x, y, name, side="r"):
    via(x, y); w = 4.6 * len(name) + 6
    fx = x + 4 if side == "r" else x - 4 - w
    L_TX.append(f'<rect x="{fx:.1f}" y="{y-4:.1f}" width="{w:.1f}" height="8" rx="4" class="flag"/>')
    txt(fx + w/2, y + 2.4, name, "ft", "middle")

def pwr(x, y, kind, down=True):
    sgn = 1 if down else -1; y2 = y + sgn*5
    path(L_AU, [(x, y), (x, y2)], "wau", 1.6)
    if kind == "vdd":
        L_VIA.append(f'<rect x="{x-5:.1f}" y="{y2-0.9:.1f}" width="10" height="1.8" rx=".9" class="vddsym"/>')
    else:
        for j, w in enumerate((10, 6.5, 3)):
            L_VIA.append(f'<rect x="{x-w/2:.1f}" y="{y2+sgn*j*1.9-0.6:.1f}" width="{w}" height="1.2" rx=".6" class="gndsym"/>')
def tft(name, x, y, flip=False, gate="l", label=True, nf=1):
    """Horizontal-channel TFT: W along x, L along y. nf>1 stacks fingers vertically. Returns pins."""
    D = dev[name]; W, L = D["W"] / nf, D["L"]; pitch = L + 16
    for f in range(nf):
        yy = y + f * pitch
        r(L_AL, x - 2, yy - 2, W + 4, L + 4, "al")                        # gate under channel (+LOV)
        r(L_DN, x - 1, yy - 7, W + 2, L + 14, "dntt", 1.5)               # DNTT island
        r(L_AU, x, yy - 7, W, 6, "au", 1); r(L_AU, x, yy + L + 1, W, 6, "au", 1)   # S/D contacts
    ym = y + (nf - 1) * pitch / 2 + L / 2
    if gate == "l": r(L_AL, x - 10, ym - 2, 9, 4, "al", 1); g = (x - 10, ym)
    else:           r(L_AL, x + W + 1, ym - 2, 9, 4, "al", 1); g = (x + W + 10, ym)
    top, bot = (x + W/2, y - 7), (x + W/2, y + (nf-1)*pitch + L + 7)
    s, d = (bot, top) if flip else (top, bot)
    tag = name if name[0].isalpha() else "M" + name
    hh = (nf - 1) * pitch + L
    if label:
        fs = 5.0 if W >= 14 else 4.2
        L_TX.append(f'<text x="{x + W/2:.1f}" y="{y + hh/2 + fs*0.36:.1f}" class="inch" style="font-size:{fs}px" text-anchor="middle">{tag}</text>')
    L_TIP.append(f'<rect x="{x-10:.1f}" y="{y-8:.1f}" width="{W+20:.1f}" height="{hh+16:.1f}" class="hit"><title>{tag}  W/L = {D["W"]:g}/{D["L"]:g} um  (d={D["d"]}, g={D["g"]}, s={D["s"]})</title></rect>')
    return dict(s=s, d=d, g=g, W=W)

def cap(name, x, y, w, label, net_top):
    C = caps[name]; area = C * 1e3 / CI_FF_UM2; h = area / w
    r(L_AL, x - 4, y - 4, w + 8, h + 8, "al", 3)
    r(L_AU, x, y, w, h, "capau", 3)
    # plate texture: fine hatch
    L_DECO.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="3" fill="url(#hatch)" opacity="0.35"/>')
    if w >= 100:
        txt(x + w/2, y + h/2 - 2, label, "cl", "middle"); txt(x + w/2, y + h/2 + 10, f"{C:g} pF · {area/1e3:.1f}k µm²", "cs", "middle")
    elif w >= 40 and label:
        txt(x + w/2, y + h/2 + 4, label, "cl", "middle")
    return h

# ---------------- floorplan constants ----------------
XC, COLW, YC, RP = 170, 330, 150, 100
NCOL, NROW = 5, 6
SENS = ["pH", "uric acid", "lactate", "temperature", "pyocyanin", "impedance"]
CHIP_W, CHIP_H = XC + NCOL * COLW + 40, 1700

# ---------------- crossbar ----------------
for i in range(NROW):
    ry = YC + i * RP; ymid = ry + 47
    # input pad + row gate line (Al)
    r(L_AU, 22, ry + 20, 78, 54, "pad", 4); via(96, ymid)
    L_DECO.append(f'<path d="M34,{ry+38} q10,-6 20,2 t20,0" class="scrub"/>')
    txt(61, ry + 66, f"IN{i+1}", "pl", "middle"); txt(61, ry + 30, SENS[i], "ps", "middle")
    path(L_AL, [(96, ymid), (XC + NCOL * COLW - 6, ymid)], "wal", 4)
    # VDD strap across the row (Au)
    path(L_AU, [(126, ry + 7), (XC + NCOL * COLW - 14, ry + 7)], "wau", 5)
    for k in range(NCOL):
        cx = XC + k * COLW
        n_p, n_m = str(1 + 6*k + i), str(31 + 6*k + i)
        # A- device (2 fingers of 19 x L10), drain -> acol (left edge)
        Dm = dev[n_m]; fw = Dm["W"] / 2
        r(L_AL, cx + 18, ymid - 7, 2*fw + 10, 14, "al")
        for f in range(2):
            fx = cx + 20 + f * (fw + 6)
            r(L_DN, fx - 1, ymid - 12, fw + 2, 24, "dntt", 1.5)
            r(L_AU, fx, ymid - 12, fw, 6, "au", 1); r(L_AU, fx, ymid + 6, fw, 6, "au", 1)
            path(L_AU, [(fx + fw/2, ymid - 12), (fx + fw/2, ry + 7)], "wau", 2.5)
            path(L_AU, [(fx + fw/2, ymid + 12), (fx + fw/2, ry + 90), (cx + 6, ry + 90)], "wau", 2.5)
        # A+ synapse bank: 10 um fingers, L = 54, each with a laser-severable fuse
        Dp = dev[n_p]; W = Dp["W"]; nf = math.ceil(W / 10 - 1e-9); bx = cx + 68; L = Dp["L"]
        r(L_AL, bx - 3, ry + 18, (nf-1)*13 + min(10, W-10*(nf-1)) + 6, L + 4, "al")
        for f in range(nf):
            fw = min(10, W - 10 * f); fx = bx + f * 13
            r(L_DN, fx, ry + 13, fw, L + 14, "dntt", 1.2)
            r(L_AU, fx, ry + 13, fw, 7, "au", 1); r(L_AU, fx, ry + 20 + L - 1, fw, 7, "au", 1)
            path(L_AU, [(fx + fw/2, ry + 13), (fx + fw/2, ry + 7)], "wau", 2.5)
            path(L_AU, [(fx + fw/2, ry + 26 + L), (fx + fw/2, ry + 82)], "fuse", 1.2)       # fuse neck
            L_DECO.append(f'<circle cx="{fx+fw/2:.1f}" cy="{ry+80:.1f}" r="2.6" class="fusemark"/>')
            path(L_AU, [(fx + fw/2, ry + 82), (fx + fw/2, ry + 86)], "wau", 2.5)
        path(L_AU, [(bx, ry + 86), (cx + COLW - 10, ry + 86)], "wau", 3.5)                 # drain collector -> ap
        L_TIP.append(f'<rect x="{bx-3}" y="{ry+12}" width="{nf*13+2}" height="{L+16}" class="hit"><title>M{n_p}  A+ synapse, class {k+1}, input {i+1}: W/L = {W:g}/{L:g} um = {W/10:g} x 10 um laser-linked fingers (d=ap{k+1}, g=row{i+1}, s=vdd)</title></rect>')
        txt(bx + nf*13/2, ry + 42, f"M{n_p}", "sl", "middle")
        txt(bx + nf*13/2, ry + 52, f"{W:g}/{L:g} · {W/10:g}×10µm", "dl", "middle")
        txt(cx + 20 + fw + 3, ry + 108 - 25, f"M{n_m}", "dl", "middle")
# VDD trunk (left) + column rails
path(L_AU, [(126, 60), (126, YC + NROW * RP - 5)], "wau", 6); flag(126, 60, "VDD")
for k in range(NCOL):
    cx = XC + k * COLW
    path(L_AU, [(cx + COLW - 10, YC + 2), (cx + COLW - 10, 915)], "rail", 4)   # ap_k
    path(L_AU, [(cx + 6, YC + 2), (cx + 6, 905), (cx + 36, 905), (cx + 36, 915)], "rail2", 3)   # acol_k
    txt(cx + COLW/2, YC - 22, f"CLASS {k+1}", "ch", "middle")
    txt(cx + COLW - 12, YC - 5, f"ap{k+1}", "nl", "end"); txt(cx + 9, YC - 5, f"acol{k+1}", "nl", "start")

# ---------------- rail capacitors + steering + readout cells ----------------
for k in range(NCOL):
    cx = XC + k * COLW; cy = 735
    h = cap(f"CRAIL{k+1}", cx + 26, cy, 270, f"C_rail{k+1}", f"ap{k+1}")
    path(L_AU, [(cx + COLW - 10, cy + 20), (cx + 296, cy + 20)], "wau", 4); via(cx + 294, cy + 20)
    pwr(cx + 30, cy + h + 4, "gnd")
    # steering switch M70+k
    st = tft(str(70 + k), cx + 16, 922, flip=False)
    flag(*st["g"], "phib", "l") if False else flag(st["g"][0], st["g"][1], "phib", "r")
    flag(st["d"][0] + 18, st["d"][1] + 3, "acom")
    path(L_AU, [st["d"], (st["d"][0], st["d"][1] + 3), (st["d"][0] + 18, st["d"][1] + 3)], "wau", 2.5)

    RY = 975; ap_x = cx + COLW - 10; b = 81 + 10*k
    # row 1
    m75 = tft(str(75 + k), cx + 40, RY + 20)
    m81 = tft(str(b), cx + 150, RY + 20, gate="r")
    path(L_AU, [(ap_x, 915), (ap_x, RY - 2), (m75["s"][0], RY - 2), m75["s"]], "rail", 4)
    path(L_AL, [m81["g"], (ap_x, m81["g"][1])], "wal", 3); via(ap_x, m81["g"][1])
    flag(m75["g"][0], m75["g"][1], "rstr", "l"); pwr(*m75["d"], "gnd")
    path(L_AU, [m81["s"], (m81["s"][0], m81["s"][1] - 3), (m81["s"][0] + 30, m81["s"][1] - 3)], "wau", 2.2); flag(m81["s"][0] + 30, m81["s"][1] - 3, "vls")
    # row 2
    m83 = tft(str(b + 2), cx + 40, RY + 72)
    m89 = tft(str(b + 8), cx + 160, RY + 72, flip=True)
    m82 = tft(str(b + 1), cx + 196, RY + 70)
    pk  = tft(str(b + 9), cx + 240, RY + 72)
    yd = RY + 50
    path(L_AU, [m81["d"], (m81["d"][0], yd), (cx + 26, yd), (cx + 26, m83["g"][1]), m83["g"]], "net", 3); via(cx + 28, m83["g"][1])
    path(L_AU, [m82["s"], (m82["s"][0], yd)], "net", 3); path(L_AU, [m89["d"], (m89["d"][0], yd)], "net", 3)
    txt(cx + 110, yd - 3, f"d{k+1}", "nl", "middle")
    pwr(*m83["s"], "vdd", down=False); pwr(*m89["s"], "vdd"); pwr(*pk["s"], "vdd", down=False); pwr(*m82["d"], "gnd")
    path(L_AL, [m89["g"], (m89["g"][0], m89["g"][1] + 21)], "wal", 2.5); flag(m89["g"][0], m89["g"][1] + 21, "lockb", "l")
    path(L_AL, [m82["g"], (m82["g"][0], m82["g"][1] + 10)], "wal", 2.5); pwr(m82["g"][0], m82["g"][1] + 10, "gnd")
    path(L_AU, [pk["d"], (pk["d"][0], pk["d"][1] + 4), (pk["d"][0] + 16, pk["d"][1] + 4)], "wau", 2.2); flag(pk["d"][0] + 16, pk["d"][1] + 4, "win")
    # row 3
    m85 = tft(str(b + 4), cx + 40, RY + 132, flip=True)
    m86 = tft(str(b + 5), cx + 116, RY + 132)
    m84 = tft(str(b + 3), cx + 196, RY + 126)
    m88 = tft(str(b + 7), cx + 240, RY + 132)
    m87 = tft(str(b + 6), cx + 296, RY + 132, flip=True)
    yna = RY + 110
    path(L_AU, [(m85["d"][0], yna), (cx + 300, yna)], "net2", 3)
    for p in (m83["d"], m85["d"], m84["s"], m88["s"]): path(L_AU, [p, (p[0], yna)], "net2", 3)
    path(L_AL, [m86["g"], (m86["g"][0] - 2, m86["g"][1]), (m86["g"][0] - 2, yna)], "wal", 2.5); via(m86["g"][0] - 2, yna)
    txt(cx + 160, yna - 3, f"na{k+1}", "nl", "middle"); flag(cx + 300, yna, f"OUT{k+1}")
    ynb = RY + 182
    path(L_AU, [m86["d"], (m86["d"][0], ynb), (m87["s"][0], ynb), m87["s"]], "net3", 3)
    path(L_AL, [m85["g"], (m85["g"][0] - 4, m85["g"][1]), (m85["g"][0] - 4, ynb), (m86["d"][0], ynb)], "wal", 2.5)
    via(m85["g"][0] - 4, ynb); via(m86["d"][0], ynb)
    path(L_AL, [pk["g"], (cx + 222, pk["g"][1]), (cx + 222, ynb)], "wal", 2.5); via(cx + 222, ynb)
    txt(cx + 180, ynb + 9, f"nb{k+1}", "nl", "middle")
    pwr(*m85["s"], "vdd"); pwr(*m86["s"], "vdd", down=False)
    pwr(*m84["d"], "gnd"); pwr(*m88["d"], "gnd"); pwr(*m87["d"], "gnd", down=False)
    path(L_AL, [m84["g"], (m84["g"][0], m84["g"][1] + 16)], "wal", 2.5); pwr(m84["g"][0], m84["g"][1] + 16, "gnd")
    path(L_AL, [m87["g"], (m87["g"][0], m87["g"][1] + 12)], "wal", 2.5); pwr(m87["g"][0], m87["g"][1] + 12, "gnd")
    path(L_AL, [m88["g"], (m88["g"][0], m88["g"][1] + 28)], "wal", 2.5); flag(m88["g"][0], m88["g"][1] + 28, "rstr")
    L_DECO.append(f'<rect x="{cx+8}" y="{RY-8}" width="{COLW-6}" height="212" rx="10" class="cellbox"/>')
    txt(cx + 16, RY + 200, f"READOUT {k+1} · compare · latch · lock", "bt")

# ---------------- global blocks ----------------
def ann(m, n, skip=()):
    D = dev[n]
    for pin in ("g", "d", "s"):
        if pin in skip: continue
        net = D[pin]; x, y = m[pin]
        if pin == "g":
            if net == "0": pwr(x, y, "gnd")
            elif net == "vdd": pwr(x, y, "vdd", down=False)
            else: flag(x, y, net, "l")
        else:
            up = (y < (m["s"][1] + m["d"][1]) / 2)
            if net == "0": pwr(x, y, "gnd", down=not up)
            elif net == "vdd": pwr(x, y, "vdd", down=not up)
            else: flag(x, y + (-4 if up else 4), net)

GY = 1235
def block(x, y, w, h, title, cls="blk"):
    L_DECO.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" class="{cls}"/>'); txt(x + 10, y + 16, title, "bt")
block(XC, GY, 700, 250, "REFERENCE · drift servo M61–64 · level shift M65/66 · C_ref sampling M67–69")
for j, n in enumerate(("61", "62", "63", "64")):
    ann(tft(n, XC + 40 + j * 62, GY + 60), n)
m65 = tft("65", XC + 330, GY + 50, nf=4); ann(m65, "65")
m66 = tft("66", XC + 570, GY + 50, nf=4); ann(m66, "66")
cap("CREF", XC + 40, GY + 160, 60, "C_ref", "ref"); flag(XC + 100, GY + 165, "ref"); txt(XC + 70, GY + 232, "24 pF · 3.4k µm²", "dl", "middle")
for j, n in enumerate(("67", "68", "69")):
    ann(tft(n, XC + 170 + j * 85, GY + 185), n)
block(XC + 720, GY, 420, 250, "LOCKOUT · win wired-OR · lockb inverter · precharge")
for j, n in enumerate(("80", "WR", "I1", "I2")):
    ann(tft(n, XC + 770 + j * 95, GY + 70), n)
cap("CWIN", XC + 770, GY + 160, 17, "", "win"); txt(XC + 792, GY + 172, "C_win 2 pF", "dl"); flag(XC + 787, GY + 164, "win")
block(XC + 1160, GY, 300, 250, "SEQ8 M133–140 · overridden in sim · to redesign (ms phases)", "blkdash")
for j, n in enumerate(("133", "134", "135", "136", "137", "138", "139", "140")):
    tft(n, XC + 1195 + (j // 4) * 130, GY + 45 + (j % 4) * 38)
cap("CA", XC + 1195, GY + 205, 16, "", "na"); txt(XC + 1217, GY + 216, "CA 1.8 pF", "dl")
cap("CB", XC + 1300, GY + 192, 51, "CB", "nb"); txt(XC + 1358, GY + 216, "CB 18 pF · 2.6k µm²", "dl")
block(XC + 1480, GY, 170, 250, "SPARES M141–145", "blkhatch")
for j, n in enumerate(("141", "142", "143", "144", "145")):
    ann(tft(n, XC + 1515 + (j % 2) * 70, GY + 55 + (j // 2) * 62), n)
txt(XC + 1490, GY + 238, "laser-linkable repair devices", "dl")

# pads row
PY = 1535; pads = ["VDD", "GND", "rstr", "rstb", "phib", "phi", "OUT1", "OUT2", "OUT3", "OUT4", "OUT5"]
for j, p in enumerate(pads):
    px = XC + j * 150
    r(L_AU, px, PY, 90, 60, "pad", 4); L_DECO.append(f'<path d="M{px+15},{PY+22} q10,-6 20,2 t20,0" class="scrub"/>')
    txt(px + 45, PY + 48, p, "pl", "middle")

# ---------------- assemble ----------------
style = """
.al{fill:#9fb0c4;opacity:.85} .wal{fill:none;stroke:#9fb0c4;stroke-linecap:round;stroke-linejoin:round;opacity:.9}
.dntt{fill:#8b6cff;opacity:.55} .au{fill:url(#gold)} .capau{fill:url(#goldcap);stroke:#ffe29a;stroke-width:1}
.pad{fill:url(#gold);stroke:#ffe7a8;stroke-width:1.2}
.wau{fill:none;stroke:#e9b54a;stroke-linecap:round;stroke-linejoin:round}
.rail{fill:none;stroke:#ffcf5c;stroke-linecap:round;stroke-linejoin:round}
.rail2{fill:none;stroke:#e0a85a;stroke-linecap:round;stroke-linejoin:round;opacity:.9}
.net{fill:none;stroke:#ffd36e;stroke-linecap:round;stroke-linejoin:round}
.net2{fill:none;stroke:#ffc24d;stroke-linecap:round;stroke-linejoin:round}
.net3{fill:none;stroke:#f5b041;stroke-linecap:round;stroke-linejoin:round}
.fuse{fill:none;stroke:#ffd98a;stroke-linecap:round} .fusemark{fill:none;stroke:#ff6b6b;stroke-width:.6;stroke-dasharray:1.2 1}
.via{fill:#1a1206;stroke:#ffd36e;stroke-width:.9}
.vddsym{fill:#ff8a65} .gndsym{fill:#7fd1ff}
.flag{fill:#10151d;stroke:#56657a;stroke-width:.6;opacity:.92}
.scrub{fill:none;stroke:#b8862c;stroke-width:1.2;opacity:.7}
.cellbox{fill:none;stroke:#e9b54a;stroke-opacity:.18;stroke-width:1.2;stroke-dasharray:6 4}
.blk{fill:#000;fill-opacity:.12;stroke:#e9b54a;stroke-opacity:.25;stroke-width:1.2}
.blkdash{fill:#000;fill-opacity:.12;stroke:#ff9f6b;stroke-opacity:.5;stroke-width:1.2;stroke-dasharray:8 5}
.blkhatch{fill:url(#hatch2);stroke:#e9b54a;stroke-opacity:.25;stroke-width:1.2}
text{font-family:'JetBrains Mono','SFMono-Regular',Menlo,Consolas,monospace}
.inch{fill:#ffffff;font-weight:700;letter-spacing:.1px} .hit{fill:transparent}
.t{fill:#d8dee9;font-size:7px} .dl{fill:#c9d4e3;font-size:5.2px;opacity:.85} .sl{fill:#fff4d6;font-size:8px;font-weight:700}
.ft{fill:#b8c4d6;font-size:5.2px} .nl{fill:#ffe6a3;font-size:6.5px;font-weight:600}
.pl{fill:#2a1a05;font-size:10px;font-weight:700} .ps{fill:#3b2608;font-size:7px}
.cl{fill:#3a2505;font-size:14px;font-weight:700} .cs{fill:#4a3009;font-size:8px}
.ch{fill:#ffe6a3;font-size:15px;font-weight:700;letter-spacing:2px} .bt{fill:#e9c77b;font-size:8px;letter-spacing:.6px}
.title{fill:#fff1cf;font-size:30px;font-weight:700;letter-spacing:1px} .sub{fill:#c9b48a;font-size:12px}
.leg{fill:#d8c7a3;font-size:10px}
"""
defs = """
<linearGradient id="foil" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3b2410"/><stop offset=".55" stop-color="#2c1a0b"/><stop offset="1" stop-color="#3d2611"/></linearGradient>
<linearGradient id="gold" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffe08a"/><stop offset=".5" stop-color="#e4ad3f"/><stop offset="1" stop-color="#b9831f"/></linearGradient>
<linearGradient id="goldcap" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffe6a0"/><stop offset=".45" stop-color="#e8b24a"/><stop offset="1" stop-color="#b47c1c"/></linearGradient>
<pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="#fff5d0" stroke-width="1"/></pattern>
<pattern id="hatch2" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="8" height="8" fill="#000" fill-opacity=".12"/><line x1="0" y1="0" x2="0" y2="8" stroke="#e9b54a" stroke-opacity=".12" stroke-width="2"/></pattern>
<pattern id="weave" width="14" height="14" patternUnits="userSpaceOnUse"><circle cx="3" cy="4" r=".7" fill="#e9b54a" fill-opacity=".10"/><circle cx="10" cy="11" r=".5" fill="#fff" fill-opacity=".05"/><path d="M0,7 h14" stroke="#000" stroke-opacity=".08"/></pattern>
<filter id="grain" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="4"/><feColorMatrix values="0 0 0 0 .9  0 0 0 0 .6  0 0 0 0 .25  0 0 0 .07 0"/><feComposite in2="SourceGraphic" operator="in"/></filter>
<filter id="glow" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="1.2" result="b"/><feColorMatrix in="b" values="1 0 0 0 0  0 .8 0 0 0  0 0 .3 0 0  0 0 0 .35 0"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>
"""
W, H = CHIP_W + 60, CHIP_H + 60
out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
       f"<defs>{defs}</defs><style>{style}</style>",
       f'<rect width="{W}" height="{H}" fill="#0a0d12"/>',
       f'<rect x="30" y="30" width="{CHIP_W}" height="{CHIP_H}" rx="26" fill="url(#foil)"/>',
       f'<rect x="30" y="30" width="{CHIP_W}" height="{CHIP_H}" rx="26" fill="url(#weave)"/>',
       f'<rect x="38" y="38" width="{CHIP_W-16}" height="{CHIP_H-16}" rx="20" fill="none" stroke="#e9b54a" stroke-opacity=".45" stroke-width="2"/>',
       '<g transform="translate(30,30)">']
for (xf, yf) in [(20, 20), (CHIP_W - 40, 20), (20, CHIP_H - 40), (CHIP_W - 40, CHIP_H - 40)]:
    out.append(f'<g opacity=".6"><path d="M{xf-8},{yf} h16 M{xf},{yf-8} v16" stroke="#e9b54a" stroke-width="2"/><circle cx="{xf}" cy="{yf}" r="5" fill="none" stroke="#e9b54a"/></g>')
out.append(f'<text x="170" y="62" class="title">Tortoise · T6</text>')
out.append(f'<text x="170" y="84" class="sub">Monolithic p-type OTFT time-race classifier · 6 inputs × 5 classes · 146 TFTs · single 3.3 V rail · no negative bias · DNTT on AlOx/SAM (0.70 µF/cm²) on polyimide</text>')
out.append(f'<text x="170" y="102" class="sub" opacity=".75">Illustrative placement (not DRC-checked). Every TFT W/L and capacitor area drawn to scale in µm from the T6 netlist; crossbar widths are pre-retraining netlist values.</text>')
# legend + scale bar
lx = CHIP_W - 640; ly = 40
items = [("al", "Al gate (bottom)"), ("dntt", "DNTT channel"), ("au", "Au S/D · interconnect"), ("fuse", "laser-link fuse"), ("via", "via"), ("flag", "global net flag"), ("vdd", "VDD"), ("gnd", "GND")]
for j, (c, lab) in enumerate(items):
    xx = lx + (j % 4) * 152; yy = ly + (j // 4) * 22
    if c in ("via",): out.append(f'<circle cx="{xx+7}" cy="{yy+6}" r="4" class="via"/>')
    elif c == "fuse": out.append(f'<circle cx="{xx+7}" cy="{yy+6}" r="5" class="fusemark" style="stroke-width:1.2"/>')
    elif c == "vdd": out.append(f'<rect x="{xx}" y="{yy+5}" width="16" height="3" rx="1.5" class="vddsym"/>')
    elif c == "gnd": out.append(f'<rect x="{xx}" y="{yy+3}" width="16" height="2" class="gndsym"/><rect x="{xx+3}" y="{yy+6.5}" width="10" height="2" class="gndsym"/><rect x="{xx+6}" y="{yy+10}" width="4" height="2" class="gndsym"/>')
    elif c == "flag": out.append(f'<rect x="{xx}" y="{yy+1}" width="16" height="10" rx="5" class="flag"/>')
    else: out.append(f'<rect x="{xx}" y="{yy}" width="16" height="12" rx="2" class="{c}"/>')
    out.append(f'<text x="{xx+24}" y="{yy+10}" class="leg">{lab}</text>')
out.append(f'<g transform="translate({lx},{ly+52})"><rect width="100" height="5" fill="#e9b54a"/><rect x="50" width="50" height="5" fill="#6b4a14"/><text y="18" class="leg">0</text><text x="100" y="18" class="leg" text-anchor="end">100 µm</text></g>')
out.append(f'<text x="{lx+130}" y="{ly+62}" class="leg">die ≈ {CHIP_W/1000:.2f} × {CHIP_H/1000:.2f} mm</text>')
out += ['<g>' + "".join(L_DECO[:0]) + '</g>', '<g>' + "".join(L_AL) + '</g>', '<g>' + "".join(L_DN) + '</g>',
        '<g filter="url(#glow)">' + "".join(L_AU) + '</g>', '<g>' + "".join(L_DECO) + '</g>',
        '<g>' + "".join(L_VIA) + '</g>', '<g>' + "".join(L_TX) + '</g>', '<g>' + "".join(L_TIP) + '</g>', '</g></svg>']
open(sys.argv[2] if len(sys.argv) > 2 else "trace2_t6_layout.svg", "w").write("\n".join(out))
print("devices drawn from netlist:", len(dev), " svg size:", W, "x", H)
