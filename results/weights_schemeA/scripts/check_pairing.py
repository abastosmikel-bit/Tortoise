"""A3 3B-V die pairing check (W11): for every new-weights die file that has a campaign counterpart available locally
(campaign draws are in Git LFS: git lfs pull --include="results/fitc10_campaign/raw/v3/phase3B_V/<file>"), the
non-crossbar V_th draws must be identical and each shared crossbar bank's draw must equal the old draw x sqrt(F_old/F_new)
(same z-score, sigma from its own area). -> summary/A3_pairing_check.json"""
import json, re
import numpy as np
import wcommon as W

if __name__ == "__main__":
    Fn = np.load(W.WEIGHTS / "FINAL_frozen.npy"); Fo = W.F_OLD
    out = []
    for f in sorted((W.RAW / "A3_FINAL_frozen/phase3B_V").glob("*_draws.json")):
        of = W.CAMP / "raw/v3/phase3B_V" / f.name
        try:
            o = json.loads(of.read_text())
        except (OSError, ValueError):
            continue                                    # LFS pointer not fetched
        n = json.loads(f.read_text())
        dmax, rat = 0.0, []
        for k in o:
            if k not in n:
                continue
            m = re.fullmatch(r"X(\d+)", k)
            if m and int(m.group(1)) <= 30:
                j = int(m.group(1)); kk, i = (j - 1) // 6, (j - 1) % 6
                rat.append(n[k]["DVTH"] / o[k]["DVTH"] / np.sqrt(Fo[i, kk] / Fn[i, kk]))
            else:
                dmax = max(dmax, abs(n[k]["DVTH"] - o[k]["DVTH"]))
        out.append(dict(file=f.name, non_crossbar_max_abs_diff_V=dmax, n_shared_banks=len(rat),
                        bank_ratio_min=float(min(rat)), bank_ratio_max=float(max(rat)),
                        only_old=sorted(set(o) - set(n)), only_new=sorted(set(n) - set(o))))
    (W.SUMM / "A3_pairing_check.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
