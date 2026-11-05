"""H4.2: recompute the host read time of finished classification runs as simulated (stop time - STOP_TAIL when the
host timer stopped the run) and, where it differs from the stored t_read by > 0.01 us, the read-time outcome from the
run's 1 us waveform. Old values are kept under 'read_fix'. Idempotent. Usage: python3 read_fix.py [glob ...]"""
import glob, gzip, json, sys
import numpy as np
import hv2

pats = sys.argv[1:] or [str(hv2.RAW / "C[1-6]*/*_s[0-9][0-9].json")]
n = ch = 0
for pat in pats:
    for f in sorted(glob.glob(pat)):
        m = json.load(open(f))
        if "build" not in m or not m.get("t_end_us") or "read_fix" in m:
            continue
        b = m["build"]
        n += 1
        if b.get("adaptive_D") is None or m["t_end_us"] >= b["t_end"] - 1.0:
            continue
        tr = m["t_end_us"] - hv2.STOP_TAIL
        if m["t_read_us"] - tr <= 0.15:   # within the stop-when overshoot (one time step): stored read time stands
            continue
        cz = f[:-5] + ".csv.gz"
        d = np.genfromtxt(gzip.open(cz, "rt"), delimiter=",", names=True)
        na = {k: float(np.interp(tr, d["t_us"], d[f"na{k}"])) for k in range(1, 6)}
        lat = [k for k in range(1, 6) if na[k] > 2.5]
        old = {k: m.get(k) for k in ("t_read_us", "latched_read", "na_read", "valid_read", "failure_read", "winner_read")}
        first = m.get("first")
        if not m["trip_us"]:
            fr = "stuck_latched" if lat else "timeout"
        elif not lat:
            fr = "none_latched"
        elif len(lat) > 1:
            fr = "multi_latched"
            if m.get("lock_us") and any(m["trip_us"].get(str(k), 0) > m["lock_us"] for k in lat):
                fr = "lockout_failed"
        elif lat[0] != first:
            fr = "latched_not_first"
        else:
            fr = None
        m.update(t_read_us=round(tr, 3), latched_read=lat, na_read={str(k): round(v, 4) for k, v in na.items()}, valid_read=fr is None,
                 failure_read=fr, winner_read=lat[0] if fr is None else None, t_rows_off_us=round(tr - 0.2 - b["READ"], 3),
                 host_timer_pre_trip_us=round(b["D"] - (tr - 0.2 - b["READ"] - min(m["trip_us"].values())), 3) if m["trip_us"] else None,
                 read_fix=dict(rule="H4.2", old=old))
        json.dump(m, open(f, "w"), indent=1, default=float)
        ch += 1
        print("fixed", f.split("/")[-1], old["latched_read"], "->", lat, fr, flush=True)
print(n, "checked,", ch, "changed")
