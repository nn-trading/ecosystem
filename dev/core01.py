# dev/core01.py
from __future__ import annotations
import os, json, time, subprocess
from pathlib import Path
from datetime import datetime
try:
    from core.ascii_writer import write_text_ascii, to_ascii
    import httpx
except Exception:
    httpx = None

ROOT = Path(__file__).resolve().parents[1]
CFG  = ROOT/"config/core.yaml"
REPORTS = ROOT/"reports"
RUNS = ROOT/"runs"

def now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def load_cfg():
    import yaml
    if CFG.exists():
        return yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}
    return {}

def write(path:Path, text:str):
    write_text_ascii(str(path), text)

def probe_network(url:str, timeout:int)->bool:
    if not httpx: return False
    try:
        r = httpx.get(url, timeout=timeout)
        return 200 <= r.status_code < 400
    except Exception:
        return False

def ensure_env(vars_):
    missing=[v for v in vars_ if not os.environ.get(v)]
    if missing:
        write(REPORTS/"core01_missing_env.txt", "Missing:\n" + "\n".join(missing))
    return not missing

def touch(files):
    for f in files:
        Path(f).parent.mkdir(parents=True, exist_ok=True)
        write_text_ascii(str(Path(f)), f"touched {now()}\n")

def plan():
    return [
        "probe_network",
        "ensure_env",
        "touch_files",
    ]

def act_step(step,cfg,status):
    if step=="probe_network":
        u = cfg.get("core01",{}).get("network_probe",{}).get("url")
        to= int(cfg.get("core01",{}).get("network_probe",{}).get("timeout_sec",5))
        ok = probe_network(u, to) if u else False
        status["network_ok"]=bool(ok)
    elif step=="ensure_env":
        req = cfg.get("core01",{}).get("required_env") or []
        status["env_ok"]=ensure_env(req)
    elif step=="touch_files":
        touch([ROOT/p for p in (cfg.get("core01",{}).get("touch_files") or [])])
        status["touched"]=True

def test_fix(status):
    # Simple fix path: if env missing, record & continue; doctor handles secrets.
    # If network down, mark degraded but keep running.
    pass

def loop_once(cfg):
    status={"ts":now(),"plan":plan(),"network_ok":None,"env_ok":None,"touched":False}
    for s in status["plan"]:
        act_step(s,cfg,status)
    test_fix(status)
    write(REPORTS/"core01_status.json", json.dumps(status, indent=2))
    return status

def run_loop():
    cfg=load_cfg()
    maxrt=int(cfg.get("core01",{}).get("max_runtime_sec",180))
    interval=int(cfg.get("core01",{}).get("loop_interval_sec",10))
    start=time.time()
    SNAP=RUNS/f"core01_{datetime.now():%Y%m%d_%H%M%S}"
    SNAP.mkdir(parents=True, exist_ok=True)
    write(SNAP/"SUMMARY.txt", f"[{now()}] CORE-01 loop start\n")
    loops=0
    while time.time()-start<maxrt:
        st=loop_once(cfg); loops+=1
        # Append compact line to snapshot
        with open(SNAP/"SUMMARY.txt", "a", encoding="ascii", errors="ignore") as f:
            f.write(to_ascii(f"[{now()}] net={st['network_ok']} env={st['env_ok']} touched={st['touched']}\n"))
        time.sleep(interval)
    write(SNAP/"DONE.txt", f"loops={loops}\n")
    print("CORE-01 READY")

if __name__=="__main__":
    run_loop()
