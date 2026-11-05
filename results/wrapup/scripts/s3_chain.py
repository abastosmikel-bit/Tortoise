"""Study 3 chain after the K runs (DECISIONS S3.2-S3.3): recalibration fit, acceptance (winner agreement >= 36/40),
CV of the 16 configs, finalists (best b134 and best b138 by CV S3), each retrained on all of T, then 40 SPICE runs on S
per finalist. Stops (and says so) if the acceptance fails. Training data only. Usage: python3 s3_chain.py"""
import json, subprocess, sys, time
import wu

K_N = 40
while len([f for f in (wu.RAW / "S3K").glob("S3K_*.json")]) < K_N:
    time.sleep(30)
subprocess.run([sys.executable, "s3_runs.py", "recal"], check=True)
fit = json.load(open(wu.SUMM / "s3_surrogate_params.json"))
ag = fit["agreement_in_sample"]
print("recal agreement", ag, flush=True)
if ag["winner"] < 36:
    print("ACCEPTANCE FAILED (S3.2): winner agreement", ag["winner"], "< 36/40; study stops before any test-set run", flush=True)
    sys.exit(1)
subprocess.run([sys.executable, "s3_train.py", "cv", "2"], check=True)
subprocess.run([sys.executable, "s3_summary.py", "cv"], check=True)
import s3_train as TR
cv = json.load(open(wu.SUMM / "s3_cv.json"))
names = []
for b, cfg in cv["finalists"].items():
    mode, m, bud = cfg.split("_")
    r = TR.train_final((mode, int(m[1:]), bud), "recal", f"S3_{cfg}")
    print("finalist", r["name"], r["Fb"], r["n_tft"], r["colsums"], flush=True)
    names.append(r["name"])
subprocess.run([sys.executable, "s3_runs.py", "S"] + names + ["3"], check=True)
subprocess.run([sys.executable, "s3_summary.py", "select"], check=True)
print("S3 CHAIN DONE: selection complete; freeze next", flush=True)
