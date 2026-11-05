"""Phase 3 robustness map on the fixed 20-sample subset (summary/phase3_subset.json). Variant 1, 2500 us window,
fitc10 warm start (nominal-corner end state, used for every point - an approximation).
 A: one-dimensional corner sweeps (rev10/sim/models/fitc10_sweep.lib). Host row levels stay at the fitc10 values
    (V1 1.82 V, V2 2.40 V): the host is not re-trimmed per corner. The nominal point is the Phase 1 run.
 B: local-mismatch Monte Carlo - ASSUMED spreads: sigma_Vth in {20, 40, 80} mV (same for every device geometry),
    sigma_mu/mu 10 %, R_C lognormal sigma 20 %; independent per-device draws incl. the crossbar; 5 dies per level
    (owner decision D8); die seed = 1000 * sigma_mV + die.
Usage: python3 phase3.py <any of A B T P> [nproc]  (T: re-trimmed sweep, P: size-scaled MC; see below)   -> raw/phase3A/, raw/phase3B/ (resumable)"""
import json, sys, time
from multiprocessing import Pool
import common as C

WARM = C.RAW / "warmstart/fitc10_warm"
SUB = json.load(open(C.CAMP / "summary/phase3_subset.json"))["subset"]
A_POINTS = [("vth045", 0.45), ("vth055", 0.55), ("vth075", 0.75), ("vth085", 0.85), ("vth095", 0.95), ("vth105", 1.05),
            ("mu050", 0.65), ("mu075", 0.65), ("mu125", 0.65)]
B_SIG_MV, B_DIES = (20, 40, 80), (1, 2, 3, 4, 5)
# Follow-ups (owner request, after the main Phase 3):
#  T: re-trimmed corner sweep - host V1/V2 follow build_A's formula for the corner's |V_th| (process window with trim).
#  P: size-scaled mismatch - every sigma x sqrt(780 um^2/(W*L)) (build_final.py convention), anchors 20/35/50 mV for V_th,
#     10 % for mu and 20 % for R_C at 780 um^2. Seed = 1000*anchor + die, so anchor-20 dies use the same underlying
#     random numbers as the flat 20 mV dies (paired comparison).
T_POINTS = [("vth075", 0.75), ("vth085", 0.85), ("vth095", 0.95), ("vth105", 1.05)]
P_ANCHOR_MV = (20, 35, 50)
#  V: V_th-only size-scaled mismatch (D13): same seeds / dies / samples as P, mu and R_C nominal.
V_ANCHOR_MV = (20, 35)


def jobs_A():
    out = C.RAW / "phase3A"
    return [dict(tag=f"A_{p}_s{i:02d}", idx=i, prior=WARM, variant=C.VAR, outdir=out, wdir="p3A", vth=vt,
                 corner=("fitc10_sweep.lib", f"fc10_{p}")) for p, vt in A_POINTS for i in SUB]


def jobs_B():
    out = C.RAW / "phase3B"
    return [dict(tag=f"B_sv{s:02d}_d{d}_s{i:02d}", idx=i, prior=WARM, variant=C.VAR, outdir=out, wdir="p3B",
                 mc=dict(seed=1000 * s + d, s_vth=s / 1000, s_mu=0.10, s_rc=0.20)) for s in B_SIG_MV for d in B_DIES for i in SUB]


def jobs_T():
    out = C.RAW / "phase3A_T"
    return [dict(tag=f"AT_{p}_s{i:02d}", idx=i, prior=WARM, variant=C.VAR, outdir=out, wdir="p3AT", vth=vt, levels_vth=vt,
                 corner=("fitc10_sweep.lib", f"fc10_{p}")) for p, vt in T_POINTS for i in SUB]


def jobs_P():
    out = C.RAW / "phase3B_P"
    return [dict(tag=f"P_an{a:02d}_d{d}_s{i:02d}", idx=i, prior=WARM, variant=C.VAR, outdir=out, wdir="p3BP",
                 mc=dict(seed=1000 * a + d, s_vth=a / 1000, s_mu=0.10, s_rc=0.20, scale="pelgrom"))
            for a in P_ANCHOR_MV for d in B_DIES for i in SUB]


def jobs_V():
    out = C.RAW / "phase3B_V"
    return [dict(tag=f"V_an{a:02d}_d{d}_s{i:02d}", idx=i, prior=WARM, variant=C.VAR, outdir=out, wdir="p3BV",
                 mc=dict(seed=1000 * a + d, s_vth=a / 1000, s_mu=0.10, s_rc=0.20, scale="pelgrom_vth"))
            for a in V_ANCHOR_MV for d in B_DIES for i in SUB]


if __name__ == "__main__":
    which = sys.argv[1]; nproc = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    jobs = ((jobs_A() if "A" in which else []) + (jobs_B() if "B" in which else [])
            + (jobs_T() if "T" in which else []) + (jobs_P() if "P" in which else []) + (jobs_V() if "V" in which else []))
    jobs = [j for j in jobs if not (j["outdir"] / f"{j['tag']}.json").exists()]
    s = time.time()
    with Pool(nproc) as p:
        for k, m in enumerate(p.imap_unordered(C.run_one, jobs), 1):
            print(f"[{k}/{len(jobs)} {time.time()-s:6.0f}s] {m['tag']} label {m['label']} latched {m.get('latched')} "
                  f"valid {m.get('valid')} {m.get('failure')} wall {m['run']['wall_s']}", flush=True)
