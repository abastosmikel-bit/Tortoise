"""Phase 0 inventory for the fitc10 campaign.

Checks (1) that the base-design files named in the campaign specification exist, (2) whether any fitc10 / fit136 / fit085
corner or resized netlist exists in the working tree or in any commit on any fetched branch, and
(3) lists the capacitors and gate-grounded devices of the frozen lab-corner build, i.e. the
candidates a "caps x5.87, every gate-grounded load 6x longer" resize would have to choose from.

Usage: python3 phase0_inventory.py [built_netlist.cir]
  built_netlist.cir defaults to /home/claude/w/sim/circuits/smoke_s81.cir (made by smoke_lab.sh).
Output: ../summary/phase0_inventory.json
"""
import json, pathlib, re, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
NET = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/home/claude/w/sim/circuits/smoke_s81.cir")

REV10_EXPECTED = [
    "rev10/HANDOFF.md", "rev10/sim/tools/build_A.py", "rev10/sim/tools/build_final.py",
    "rev10/sim/tools/t11.py", "rev10/sim/tools/run_diag.py", "rev10/sim/tools/score.py",
    "rev10/sim/tools/lockmeas.py", "rev10/sim/tools/audit.py",
    "rev10/sim/circuits/t5L_x2_v085.cir", "rev10/sim/circuits/t5L_x2_v115.cir",
    "rev10/sim/models/trace2_otft_v2.sub", "rev10/sim/models/trace2_otft_seg.sub",
    "rev10/sim/models/vth_sweep.lib", "rev10/eval/F_hw_m4_firstpass.npy", "rev10/eval/schemeA.py",
    "data/trace2_data.npz",
]
PATTERN = r"fitc10|fit136|fit085|c10.?dntt|5\.87"


def git(*a):
    return subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True).stdout


def main():
    out = {"repo_head": git("rev-parse", "HEAD").strip()}
    out["rev10_files"] = {f: (REPO / f).exists() for f in REV10_EXPECTED}

    # working tree search (excluding this campaign's own folder, which names the corner)
    hits = git("grep", "-n", "-i", "-I", "-E", PATTERN, "--", ".", ":!results/fitc10_campaign").splitlines()
    out["worktree_hits"] = hits

    # every commit on every ref: does any file path or content mention a fitted corner?
    refs = git("for-each-ref", "--format=%(refname)").split()
    out["refs_searched"] = refs
    hist = []
    for c in sorted(set(git("rev-list", *refs).split())):
        for line in git("grep", "-l", "-i", "-I", "-E", PATTERN, c, "--", ".",
                        ":!results/fitc10_campaign").splitlines():
            hist.append(line)
    out["history_hits"] = sorted(set(hist))
    corner_libs = [l for l in (REPO / "rev10/sim/models/vth_sweep.lib").read_text().splitlines()
                   if l.startswith(".lib")]
    out["corners_in_vth_sweep_lib"] = [l.split()[1] for l in corner_libs]

    # sizing candidates in the frozen lab-corner build
    if NET.exists():
        t = NET.read_text().splitlines()
        out["built_netlist"] = str(NET)
        out["capacitors"] = [l.split("$")[0].strip() for l in t if re.match(r"^C\S+\s", l)]
        out["gate_grounded_tfts"] = [l.split("$")[0].strip() for l in t
                                     if re.match(r"^X\S+\s+\S+\s+0\s+\S+\s+potft", l)]
        out["n_tft"] = sum(1 for l in t if re.match(r"^X\S+\s.*potft", l))
    else:
        out["built_netlist"] = None

    dst = HERE.parent / "summary" / "phase0_inventory.json"
    dst.write_text(json.dumps(out, indent=1))
    missing = [f for f, ok in out["rev10_files"].items() if not ok]
    print("rev10 files missing:", missing or "none")
    print("fitted-corner hits (worktree):", hits or "none")
    print("fitted-corner hits (history, file names):", out["history_hits"] or "none")
    print("corners in vth_sweep.lib:", out["corners_in_vth_sweep_lib"])
    if NET.exists():
        print(f"{out['n_tft']} TFTs; capacitors: {len(out['capacitors'])}; gate-grounded TFTs: {len(out['gate_grounded_tfts'])}")
        for l in out["gate_grounded_tfts"]:
            print("   ", l)
    print("wrote", dst)


if __name__ == "__main__":
    main()
