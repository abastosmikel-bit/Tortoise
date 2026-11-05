"""Regenerate the B2 and B4 tables inside REPORT.md (between <!-- B2_TABLE --> / <!-- B4_TABLE --> markers)
from summary/b2_retrim.json and summary/b4_aging.json."""
import json, re
import eh

R = eh.EH / "REPORT.md"


def b2():
    r = json.load(open(eh.SUMM / "b2_retrim.json"))
    P = r["points"]
    out = []
    for v in ("0.65", "0.85"):
        out.append(f"\n**|V_th| {v} V** (zero offset: {P.get(f'v{v}_dV1+0_dV2+0', {}).get('correct', '-')}/20). "
                   "Cells: correct / valid / strict (a trip during integration counts as a failure); failures.\n")
        out.append("| Offset (mV) | V₁ swept (V₂ formula) | V₂ swept (V₁ formula) |\n|---|---|---|")
        for o in range(-200, 201, 25):
            cells = []
            for k in (f"v{v}_dV1{o:+d}_dV2+0", f"v{v}_dV1+0_dV2{o:+d}"):
                p = P.get(k)
                if p and p["n"] == 20:
                    f = ", ".join(f"{a} {b}" for a, b in p["failures"].items())
                    cells.append(f"{p['correct']} / {p['valid']} / {p['strict_correct']}" + (f" ({f})" if f else "")
                                 + (f"; race {p['race_median_us']:.0f} µs" if p['race_median_us'] else ""))
                else:
                    cells.append("not run" if o % 50 else "pending")
            if o % 50 == 0 or any(c not in ("not run",) for c in cells):
                out.append(f"| {o:+d} | {cells[0]} | {cells[1]} |")
        b = r["bands"].get(v, {})
        out.append(f"\nBand within 5 points of nominal: V₁ {b.get('V1', {}).get('band_mV')} mV, V₂ {b.get('V2', {}).get('band_mV')} mV.")
    return "\n".join(out)


def b4():
    f = eh.SUMM / "b4_aging.json"
    if not f.exists():
        return "\n(no B4 runs finished yet)\n"
    r = json.load(open(f))
    out = []
    for pol, name in (("none", "No re-trim (1.82 / 2.40 V)"), ("ideal", "Ideal re-trim (formula at the true |V_th|)")):
        mp = r.get(pol, {})
        out.append(f"\n**{name}.** Cells: correct / valid of 20 (failures; median race from C2).\n")
        out.append("| ΔV_th \\ µ | ×1 | ×0.7 | ×0.5 |\n|---|---|---|---|")
        for dv in (0.0, 0.20, 0.35):
            row = []
            for mu in (1.0, 0.70, 0.50):
                c = mp.get(f"{0.65 + dv:.2f}_{mu:.2f}")
                if not c:
                    row.append("pending")
                    continue
                f = ", ".join(f"{a} {b}" for a, b in c["failures"].items())
                row.append(f"{c['correct']} / {c['valid']}" + (f" ({f})" if f else "")
                           + (f"; {c['race_median_us']:.0f} µs" if c["race_median_us"] else ""))
            out.append(f"| +{dv:.2f} V (\\|V_th\\| {0.65 + dv:.2f}) | " + " | ".join(row) + " |")
    return "\n".join(out)


t = R.read_text()
for tag, fn in (("B2_TABLE", b2), ("B4_TABLE", b4)):
    t = re.sub(rf"<!-- {tag} -->.*?<!-- /{tag} -->", lambda m: f"<!-- {tag} -->\n{fn()}\n<!-- /{tag} -->", t, flags=re.S)
R.write_text(t)
print("tables updated")
