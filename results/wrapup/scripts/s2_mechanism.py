"""Study 2, step 1: the 0.49 V failure mechanism, from stored node voltages (no simulation).
Reads the 1 us waveforms (LFS *.csv.gz: ap, na, nb, d, ref, win, lockb, vls, timing lines) of the host_v21 E1 runs at
|V_th| 0.49 / 0.51 / 0.53 / 0.55 / 0.61 V (v2.1) and of the host_v2 C3 nominal cell (0.65 V), all 20 subset samples.
Per run it records, in the race phase (C2 start .. end of the run):
  win and lockb at C2 start + 100 us (no class latched yet), the lock devices' V_SG = VDD - lockb, the P_k pull-ups'
  V_SG = VDD - nb (losing classes), the leading class's lowest d, its rail at that time, the highest na of the leading
  class, and the run outcome.
Output: summary/s2_mechanism.json, summary/s2_mechanism.md."""
import gzip, json, pathlib, statistics
import numpy as np
import wu

PTS = [("0.49", wu.HV21RAW / "E1", "E1_v0490_m100_v21_s{:02d}"), ("0.51", wu.HV21RAW / "E1", "E1_v0510_m100_v21_s{:02d}"),
       ("0.53", wu.HV21RAW / "E1", "E1_v0530_m100_v21_s{:02d}"), ("0.55", wu.HV21RAW / "E1", "E1_v0550_m100_v21_s{:02d}"),
       ("0.61", wu.HV21RAW / "E1", "E1_v0610_m100_v21_s{:02d}"), ("0.65", wu.HV2RAW / "C3", "C3_v0650_m100_learned_s{:02d}")]


def wave(f):
    with gzip.open(f, "rt") as g:
        h = g.readline().strip().split(",")
        d = np.loadtxt(g, delimiter=",")
    return {k: d[:, i] for i, k in enumerate(h)}


def one(m, w):
    t = w["t_us"]
    tc2 = m["build"]["tC2"]
    tend = m.get("t_read_us") or t[-1]
    i100 = np.searchsorted(t, tc2 + 100)
    sl = (t >= tc2) & (t <= tend)
    # leading class = the class whose rail is highest 100 us after C2 start (the one the race will favour)
    lead = int(np.argmax([w[f"ap{k}"][i100] for k in range(1, 6)])) + 1
    dl = w[f"d{lead}"][sl]
    j = int(np.argmin(dl))
    tt = t[sl]
    losers = [k for k in range(1, 6) if k != lead]
    return dict(mode=m.get("mode", "G"), outcome=m.get("failure_read") or "valid", correct=bool(m.get("valid_read")) and m.get("winner_read") == m.get("label"),
                win_c2p100=float(w["win"][i100]), lockb_c2p100=float(w["lockb"][i100]),
                vsg_lock_c2p100=3.3 - float(w["lockb"][i100]),
                vsg_pk_losers_c2p100=float(np.median([3.3 - w[f"nb{k}"][i100] for k in losers])),
                ref_c2=float(np.interp(tc2, t, w["ref"])), vls_c2=float(np.interp(tc2, t, w["vls"])),
                lead=lead, d_lead_min=float(dl[j]), t_d_lead_min=float(tt[j]), ap_lead_at_dmin=float(w[f"ap{lead}"][sl][j]),
                vsg_trip_max=3.3 - float(dl[j]), na_lead_max=float(np.max(w[f"na{lead}"][sl])),
                lockb_at_dmin=float(w["lockb"][sl][j]), win_at_dmin=float(w["win"][sl][j]))


def main():
    out = {}
    for name, rd, pat in PTS:
        rows = []
        for i in wu.SUB:
            f = rd / (pat.format(i) + ".csv.gz")
            m = json.load(open(rd / (pat.format(i) + ".json")))
            r = one(m, wave(f))
            r["idx"] = i
            rows.append(r)
        med = lambda k: round(statistics.median(r[k] for r in rows), 4)
        rng = lambda k: [round(min(r[k] for r in rows), 4), round(max(r[k] for r in rows), 4)]
        keys = ["win_c2p100", "lockb_c2p100", "vsg_lock_c2p100", "vsg_pk_losers_c2p100", "ref_c2", "vls_c2", "d_lead_min",
                "ap_lead_at_dmin", "vsg_trip_max", "na_lead_max", "lockb_at_dmin", "win_at_dmin"]
        out[name] = dict(n=len(rows), source=str(rd.relative_to(wu.REPO)) + "/" + pat.format(0)[:-2] + "*",
                         correct=sum(r["correct"] for r in rows), outcomes={o: sum(r["outcome"] == o for r in rows) for o in sorted({r["outcome"] for r in rows})},
                         median={k: med(k) for k in keys}, range={k: rng(k) for k in keys}, runs=rows)
    (wu.SUMM / "s2_mechanism.json").write_text(json.dumps(out, indent=1))
    L = ["| \\|V_th\\| (V) | correct / 20 | outcomes | win at C2+100 µs | lockb at C2+100 µs | lock-device V_SG | P_k V_SG (losers) | lowest d of leading class | trip-driver V_SG max | leading na max |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for name, r in out.items():
        md, rg = r["median"], r["range"]
        f = lambda k: f"{md[k]:.3f} ({rg[k][0]:.3f}–{rg[k][1]:.3f})"
        L.append(f"| {name} | {r['correct']} | {', '.join(f'{k} {v}' for k, v in r['outcomes'].items())} | {f('win_c2p100')} | {f('lockb_c2p100')} | "
                 f"{f('vsg_lock_c2p100')} | {f('vsg_pk_losers_c2p100')} | {f('d_lead_min')} | {f('vsg_trip_max')} | {f('na_lead_max')} |")
    (wu.SUMM / "s2_mechanism.md").write_text("Median (range) over the 20 subset samples; V.\n\n" + "\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
