# dev/core04_mt5.py
from __future__ import annotations
import json, sys
from pathlib import Path
from datetime import datetime
ROOT = Path(__file__).resolve().parents[1]
REP  = ROOT/"reports"; RUNS = ROOT/"runs"
def now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def w(p, obj): p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(obj, indent=2), encoding="utf-8")
def probe():
    out = {"ts": now(), "ok": False, "error": None, "version": None, "account": None, "ticks": {}}
    try:
        import MetaTrader5 as mt5
    except Exception as e:
        out["error"] = f"import MetaTrader5 failed: {e}"
        w(REP/"mt5_probe.json", out); return out
    try:
        if not mt5.initialize():
            out["error"] = f"initialize failed: {mt5.last_error()}"
            w(REP/"mt5_probe.json", out); return out
        out["version"] = mt5.version()
        ai = mt5.account_info()
        out["account"] = {"login": getattr(ai, "login", None), "server": getattr(ai, "server", None)} if ai else None
        for sym in ("EURUSD","GBPUSD","USDJPY"):
            try:
                t = mt5.symbol_info_tick(sym)
                out["ticks"][sym] = {"ok": bool(t), "bid": getattr(t, "bid", None), "ask": getattr(t, "ask", None)}
            except Exception as e:
                out["ticks"][sym] = {"ok": False, "err": str(e)}
        out["ok"] = True
    except Exception as e:
        out["error"] = str(e)
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass
    w(REP/"mt5_probe.json", out)
    snap = RUNS/f"mt5_probe_{datetime.now():%Y%m%d_%H%M%S}"; snap.mkdir(parents=True, exist_ok=True)
    (snap/"SUMMARY.txt").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out
if __name__=="__main__":
    r = probe()
    print("MT5_PROBE_OK:", r.get("ok"))
