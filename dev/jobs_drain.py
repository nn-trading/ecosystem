# dev/jobs_drain.py  (ASCII)
import time, argparse
from dev import jobs_queue as jq
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--loops", type=int, default=5)
    ap.add_argument("--interval", type=float, default=1)
    args=ap.parse_args()
    n=0
    while n<args.loops:
        j=jq.pick_one()
        if j:
            ok,msg=jq.do_job(j)
            jq.complete(j["id"], ok, msg if not ok else "")
        time.sleep(args.interval)
        n+=1
    print("drain_complete")
if __name__=="__main__": main()
