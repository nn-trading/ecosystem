# dev/jobs_drain.py (ASCII)
import sys, time, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rp = str(ROOT)
if rp not in sys.path:
    sys.path.insert(0, rp)

try:
    from dev import jobs_queue as jq
except Exception:
    try:
        import jobs_queue as jq  # fallback if run from project root
    except Exception as e:
        print("import_error:", e)
        raise

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--loops", type=int, default=5)
    ap.add_argument("--interval", type=float, default=1.0)
    args = ap.parse_args()
    n = 0
    while n < args.loops:
        j = jq.pick_one()
        if j:
            ok, msg = jq.do_job(j)
            jq.complete(j["id"], ok, msg if not ok else "")
        time.sleep(args.interval)
        n += 1
    print("drain_complete")

if __name__ == "__main__":
    main()
