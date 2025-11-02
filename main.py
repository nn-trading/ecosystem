# C:\bots\ecosys\main.py
from __future__ import annotations
import os, asyncio, textwrap, json, datetime, sqlite3, time
from typing import List, Dict, Any
from core.ascii_writer import write_jsonl_ascii, write_text_ascii

ASSISTANT_CONFIG_PATH = os.environ.get("ASSISTANT_CONFIG_PATH", r"C:\bots\assistant\config.json")

def _load_assistant_config():
    try:
        with open(ASSISTANT_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _assistant_log_path(cfg):
    log_dir = (
        os.environ.get("ASSISTANT_LOG_DIR")
        or cfg.get("log_dir")
        or os.environ.get("ECOSYS_ASSISTANT_LOG_DIR")
        or os.path.join(_repo_root(), "logs")
    )
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception:
        pass
    return os.path.join(log_dir, "assistant.jsonl")

def _iso_now():
    try:
        return datetime.datetime.now().isoformat()
    except Exception:
        return ""

def _append_assistant_jsonl(obj: dict):
    cfg = _load_assistant_config()
    path = _assistant_log_path(cfg)
    try:
        write_jsonl_ascii(path, obj)
        ascii_line = json.dumps(obj, ensure_ascii=True)
        try:
            db = os.environ.get("ECOSYS_MEMORY_DB", cfg.get("memory_db") or os.path.join(_repo_root(), "var", "events.db"))
            con = sqlite3.connect(db)
            cur = con.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT)")
            cur.execute("INSERT OR REPLACE INTO kv(key,value) VALUES (?,?)", ("assistant_jsonl_size", str(os.path.getsize(path))))
            cur.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, session_id TEXT, key TEXT, value TEXT)")
            cur.execute("INSERT INTO notes(ts, session_id, key, value) VALUES (?,?,?,?)", (time.time(), cfg.get("last_session") or "", "assistant_log_append", ascii_line[:500]))
            con.commit(); con.close()
        except Exception:
            pass
    except Exception:
        pass

# --- Core ---
from core.bus import EventBus
from core.llm_client import LLMClient
from core.tools import REGISTRY as ToolsRegistry
from core.memory import Memory, DEFAULT_KEEP_LAST
from core.assistant_loader import AssistantLoader
from core.event_bridge import bridge_chat_to_bus, bridge_topics_to_bus
from memory.eventlog import EventLog
from memory.logger_db import get_logger_db

# --- Agents ---
from agents.comms_agent import CommsAgent
from agents.brain_agent import BrainAgent
from agents.worker_agent import WorkerAgent
from agents.tester_agent import TesterAgent
from agents.logger_agent import LoggerAgent

# Optional Autofix
try:
    from agents.autofix_agent import AutofixAgent
    HAS_AUTOFIX = True
except Exception:
    HAS_AUTOFIX = False

BANNER = """
--------------------------------------------------------------------------------
GPT-5 Desktop Ecosystem ready. Type your instruction. '/status' or '/tools' or '/summary' or '/memstats' or '/model' or '/setmodel <name>' or '/resummarize' or 'exit'
--------------------------------------------------------------------------------
""".strip()


# --- Helpers: ASCII sanitize and TASKS.md writer ---
# --- Helpers: Proof artifacts (ToolsRegistry, descriptors) ---

def _write_tools_proof(tools) -> None:
    try:
        repo = _repo_root()
        proof_dir = os.path.join(repo, "logs", "proofs")
        os.makedirs(proof_dir, exist_ok=True)
        # Tools names
        try:
            names = tools.available() if hasattr(tools, "available") else []
        except Exception:
            names = []
        names = names or []
        write_text_ascii(os.path.join(proof_dir, "tools_registry_names.txt"), "\n".join([str(n) for n in names]))
        # Descriptor keys
        desc_keys = []
        try:
            from core.tools import TOOL_DESCRIPTORS as _TD
            desc_keys = sorted(list(_TD.keys()))
        except Exception:
            desc_keys = []
        write_text_ascii(os.path.join(proof_dir, "tool_descriptors_keys.txt"), "\n".join([str(k) for k in desc_keys]))
        # AutoAcquire env snapshot
        try:
            info = {
                "AGENT_DANGER_MODE": str(os.environ.get("AGENT_DANGER_MODE", "0")),
                "AUTOACQUIRE_MAX": str(os.environ.get("AUTOACQUIRE_MAX", "2")),
            }
            write_text_ascii(os.path.join(proof_dir, "autoacquire_env.txt"), "\n".join([f"{k}={v}" for k, v in info.items()]))
        except Exception:
            pass
    except Exception:
        pass



# --- Helpers: PID files and cleanup ---

def _repo_root() -> str:
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except Exception:
        return os.getcwd()


def _ensure_dir(path: str) -> None:
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass


def _write_pid_files() -> None:
    repo = _repo_root()
    logs_dir = os.path.join(repo, "logs")
    _ensure_dir(logs_dir)
    pid = os.getpid()
    try:
        for name in ("ecosys_pid.txt", "headless_pid.txt"):
            try:
                with open(os.path.join(logs_dir, name), "w", encoding="ascii", errors="ignore") as f:
                    f.write(str(pid))
            except Exception:
                pass
    except Exception:
        pass


def _cleanup_orphan_backups() -> None:
    try:
        repo = _repo_root()
        dirs = [os.path.join(repo, "logs"), os.path.join(repo, "workspace", "logs")]
        for d in dirs:
            try:
                if not os.path.isdir(d):
                    continue
                for fn in os.listdir(d):
                    if fn.startswith("events_backup_") and fn.endswith(".jsonl"):
                        fp = os.path.join(d, fn)
                        try:
                            os.remove(fp)
                        except Exception:
                            pass
            except Exception:
                pass
    except Exception:
        pass


def _sanitize_ascii(text: str) -> str:
    try:
        return text.encode("ascii", "ignore").decode("ascii", "ignore")
    except Exception:
        return "".join(ch for ch in str(text) if ord(ch) < 128)


def _assistant_log_dir() -> str:
    cfg = _load_assistant_config()
    return (
        os.environ.get("ASSISTANT_LOG_DIR")
        or cfg.get("log_dir")
        or os.environ.get("ECOSYS_ASSISTANT_LOG_DIR")
        or os.path.join(_repo_root(), "logs")
    )


def _write_tasks_md() -> None:
    try:
        log_dir = _assistant_log_dir()
        tasks_path = os.path.join(log_dir, "tasks.json")
        repo = _repo_root()
        out_md = os.path.join(repo, "TASKS.md")
        tasks = []
        if os.path.exists(tasks_path):
            try:
                with open(tasks_path, "r", encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)
                if isinstance(data, dict) and isinstance(data.get("tasks"), list):
                    tasks = data.get("tasks") or []
                elif isinstance(data, list):
                    tasks = data
            except Exception:
                tasks = []
        lines = ["# Tasks", ""]
        if not tasks:
            lines.append("(no tasks found)")
        else:
            for t in tasks:
                try:
                    tid = str(t.get("id") or t.get("title") or "").strip()
                    title = str(t.get("title") or tid)
                    status = str(t.get("status") or "todo")
                    note = str(t.get("notes") or "")
                    line = f"* [{status}] {title}"
                    if tid and tid != title:
                        line += f" (id: {tid})"
                    if note:
                        line += f" - {note}"
                    lines.append(_sanitize_ascii(line))
                except Exception:
                    pass
        text = "\n".join(lines) + "\n"
        write_text_ascii(out_md, text)
    except Exception:
        pass



async def ui_printer(bus: EventBus):
    async for env in bus.subscribe("ui/print"):
        payload = env.payload or {}
        text = payload.get("text") or ""
        if text:
            try:
                safe = text.encode("ascii", "ignore").decode("ascii", "ignore")
            except Exception:
                safe = "".join(ch for ch in text if ord(ch) < 128)
            if safe:
                print(f"AI: {safe}")

async def summary_printer(bus: EventBus):
    async for env in bus.subscribe("memory/summary"):
        txt = (env.payload or {}).get("text") or ""
        if txt:
            try:
                safe = txt.encode("ascii", "ignore").decode("ascii", "ignore")
            except Exception:
                safe = "".join(ch for ch in txt if ord(ch) < 128)
            if safe:
                print(f"AI: [Summary] {safe}")
            # Update ASCII-safe TASKS.md on each summary to keep snapshot fresh
            try:
                _write_tasks_md()
            except Exception:
                pass

async def bus_recorder(bus: EventBus, memory: Memory):
    async for env in bus.subscribe_prefix(""):
        try:
            await memory.append_event(env.topic, env.payload, sender=env.sender, job_id=env.job_id)
        except Exception:
            pass

def _watch_task(label: str, task: asyncio.Task):
    def _cb(t: asyncio.Task):
        try:
            exc = t.exception()
        except asyncio.CancelledError:
            return
        except Exception as e:
            print(f"AI: [FATAL] {label} crashed: {e!r}")
            return
        if exc:
            print(f"AI: [FATAL] {label} crashed: {exc!r}")
    task.add_done_callback(_cb)

async def input_loop(bus: EventBus, llm: LLMClient, tools, memory: Memory):
    try:
        print(BANNER)
    except Exception:
        print("GPT-5 Desktop Ecosystem ready.")
    loop = asyncio.get_running_loop()
    async def ainput(prompt: str = "") -> str:
        return await loop.run_in_executor(None, lambda: input(prompt))
    while True:
        try:
            line = await ainput("")
        except (EOFError, KeyboardInterrupt):
            break
        s = (line or "").strip()
        if not s:
            continue
        if s.startswith("/"):
            parts = s.split(" ", 1)
            cmd = parts[0]; arg = parts[1] if len(parts) > 1 else ""
            _append_assistant_jsonl({"ts": _iso_now(), "event": "user_command", "cmd": cmd, "arg": arg})
            if cmd == "/tools":
                try:
                    avail = tools.available() if hasattr(tools, "available") else []
                except Exception:
                    avail = []
                print(f"AI: Tools: {', '.join(avail)}"); continue
            if cmd == "/status":
                print("AI: System online. Agents running."); continue
            if cmd == "/memstats":
                st = memory.stats()
                pretty = "\n".join(f"- {k}: {v}" for k, v in st.items())
                print("AI: Memstats:\n" + textwrap.indent(pretty, "    ")); continue
            if cmd == "/summary":
                await bus.publish("ui/print", {"text": "[Main] Requesting recent summary..."}, sender="Main")
                await bus.publish("task/new", {"text": "/summary (request recent summary)"}, sender="Main")
                continue
            if cmd == "/model":
                print(f"AI: Model: {getattr(llm, 'model', None)}"); continue
            if cmd == "/setmodel":
                name = arg.strip() or os.environ.get("LLM_MODEL", "")
                if not name:
                    print("AI: usage: /setmodel <name>")
                else:
                    try:
                        if hasattr(llm, "set_model"):
                            llm.set_model(name)  # type: ignore
                        else:
                            setattr(llm, "model", name)
                        os.environ["LLM_MODEL"] = name
                        print(f"AI: Model set to {name}")
                    except Exception as e:
                        print(f"AI: Failed to set model: {e}")
                continue
            if cmd == "/resummarize":
                await bus.publish("ui/print", {"text": "[Main] Resummarize requested."}, sender="Main")
                await bus.publish("log/resummarize", {"hint": "user requested"}, sender="Main")
                continue
            print(f"AI: Unknown command '{cmd}'."); continue
        print(f"Me: {s}")
        await bus.publish("user/text", {"text": s}, sender="User")

async def main():
    # Force working directory to repo root so EventLog paths resolve correctly
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        pass

    # Early runtime bookkeeping: PID files, orphan log backups, ASCII-safe tasks snapshot
    try:
        _write_pid_files()
    except Exception:
        pass
    try:
        _cleanup_orphan_backups()
    except Exception:
        pass
    try:
        _write_tasks_md()
    except Exception:
        pass

    _append_assistant_jsonl({"ts": _iso_now(), "event": "ecosys_start", "note": "bootstrap main()"})

    bus = EventBus()
    llm = LLMClient(timeout_sec=int(os.environ.get("LLM_TIMEOUT_SEC", "45")))
    memory = Memory()
    tools = ToolsRegistry

    # Initialize SQLite logger DB for tool events and artifacts
    try:
        _loggerdb = get_logger_db()
    except Exception:
        _loggerdb = None

    try:
        def _tools_trace(topic: str, payload: dict):
            try:
                if _loggerdb is not None:
                    try:
                        _loggerdb.log_tool_event(topic, payload)
                    except Exception:
                        pass
                loop = asyncio.get_running_loop()
                loop.create_task(bus.publish(topic, payload, sender="ToolsRegistry"))
            except Exception:
                pass
        if hasattr(tools, "set_tracer"):
            tools.set_tracer(_tools_trace)  # type: ignore[attr-defined]
    except Exception:
        pass

    # Print ToolsRegistry at startup for visibility/debug
    try:
        avail = tools.available() if hasattr(tools, "available") else []
        if isinstance(avail, list) and avail:
            print("AI: ToolsRegistry:", ", ".join(avail))
            try:
                await bus.publish("ui/print", {"text": "[Main] Tools: " + ", ".join(avail)}, sender="Main")
            except Exception:
                pass
    except Exception:
        pass

    # Write ToolsRegistry proof artifacts (single invocation)
    try:
        _write_tools_proof(tools)
    except Exception:
        pass
    # Optional runtime proofs to validate AutoAcquire and tracing
    try:
        if str(os.environ.get("OMEGA_PROOFS", os.environ.get("TOOLS_PROOF", "0"))).strip().lower() in ("1", "true", "yes"):
            repo = _repo_root(); proof_dir = os.path.join(repo, "logs", "proofs")
            os.makedirs(proof_dir, exist_ok=True)
            import json as _json
            pdf_path = os.path.join(repo, "data", "_missing.pdf")
            try:
                if os.path.exists(pdf_path):
                    probe = tools.call("pdf.to_text", path=pdf_path, max_pages=1)
                else:
                    probe = {"ok": True, "skipped": "missing file", "path": pdf_path}
            except Exception as _e:
                probe = {"ok": False, "error": f"{type(_e).__name__}: {_e}"}
            write_text_ascii(os.path.join(proof_dir, "autoacquire_probe.txt"), _sanitize_ascii(_json.dumps(probe, ensure_ascii=True)))
            # Also probe repo.search and registry list
            try:
                search = tools.call("repo.search", root=repo, query="FINDSTR", regex=False, icase=True, max_results=50)
                write_text_ascii(os.path.join(proof_dir, "repo_search_probe.json"), _sanitize_ascii(_json.dumps(search, ensure_ascii=True)))
            except Exception:
                pass
            try:
                names = tools.available() if hasattr(tools, "available") else []
                write_text_ascii(os.path.join(proof_dir, "tools_registry_probe.txt"), "\n".join([str(n) for n in (names or [])]))
            except Exception:
                pass
    except Exception:
        pass

    ui_tasks: List[asyncio.Task] = []
    t1 = asyncio.create_task(ui_printer(bus), name="ui_printer")
    t2 = asyncio.create_task(summary_printer(bus), name="summary_printer")
    _watch_task("ui_printer", t1); _watch_task("summary_printer", t2)
    ui_tasks += [t1, t2]
    await asyncio.sleep(0)

    # Re-emit resume after UI subscribers ready
    try:
        # Also print to stdout to ensure background redirection captures resume markers
        try:
            print("AI: [Main] About to publish resume")
        except Exception:
            pass
        await bus.publish("ui/print", {"text": "[Main] About to publish resume..."}, sender="Main")
        loader = AssistantLoader()
        await loader.publish_resume(bus)
        try:
            print("AI: [Main] publish_resume completed")
        except Exception:
            pass
        await bus.publish("ui/print", {"text": "[Main] publish_resume completed"}, sender="Main")
    except Exception as e:
        try:
            msg = f"[Main] publish_resume exception: {e}"
            print("AI: " + msg)
            await bus.publish("ui/print", {"text": msg}, sender="Main")
        except Exception:
            pass

    # Recorder and rotation
    enable_jsonl = str(os.environ.get("ENABLE_JSONL_RECORDER", "1")).strip().lower() not in ("0", "false", "no", "off")
    if enable_jsonl:
        rec_task = asyncio.create_task(bus_recorder(bus, memory), name="bus_recorder")
        _watch_task("bus_recorder", rec_task)
    else:
        try:
            print("AI: [Main] JSONL recorder disabled via ENABLE_JSONL_RECORDER")
        except Exception:
            pass

    async def _rotate_loop():
        try:
            keep_last = int(os.environ.get("MEM_KEEP_LAST", str(DEFAULT_KEEP_LAST)))
        except Exception:
            keep_last = DEFAULT_KEEP_LAST
        while True:
            try:
                await asyncio.sleep(int(os.environ.get("MEM_ROTATE_SEC", "60")))
                await memory.rotate_keep_last(keep_last)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(60)
    if enable_jsonl:
        rot_task = asyncio.create_task(_rotate_loop(), name="mem_rotate_loop")
        _watch_task("mem_rotate_loop", rot_task)
    else:
        try:
            print("AI: [Main] Rotation disabled because JSONL recorder is disabled")
        except Exception:
            pass

    # Bridges: service-only ctrl + chat bridge
    ctrl_topics = ["log/resummarize", "system/health", "system/heartbeat"]
    ctrl_task = asyncio.create_task(bridge_topics_to_bus(bus, ctrl_topics, poll_sec=1.0), name="bridge_topics_to_bus")
    _watch_task("bridge_topics_to_bus", ctrl_task)

    chat_task = asyncio.create_task(bridge_chat_to_bus(bus, poll_sec=1.0), name="bridge_chat_to_bus")
    _watch_task("bridge_chat_to_bus", chat_task)
    await bus.publish("ui/print", {"text": f"[Main] Bridges ready. CWD={os.getcwd()}"}, sender="Main")

    # Emergency Notepad executor (deterministic plan/exec) with debounce
    plan_seen = set()
    _emerg_pending = {}
    async def _plan_watcher():
        async for penv in bus.subscribe("task/plan"):
            try:
                jid = getattr(penv, "job_id", None)
                if jid:
                    plan_seen.add(jid)
                    t = _emerg_pending.pop(jid, None)
                    if t:
                        t.cancel()
            except Exception:
                pass
    plan_task = asyncio.create_task(_plan_watcher(), name="plan_watcher")
    _watch_task("plan_watcher", plan_task)

    async def _emergency_notepad_exec():
        async for env in bus.subscribe("task/new"):
            try:
                payload = env.payload if isinstance(env.payload, dict) else (env.payload or {})
                text = str(payload.get("text") or payload.get("content") or "")
                if not text:
                    continue
                tl = text.lower()
                if "open notepad" in tl and "type exactly:" in tl:
                    idx = tl.find("type exactly:")
                    content = text[idx + len("type exactly:"):].strip().strip('"').strip("'")
                    jid = getattr(env, "job_id", None)
                    async def _delayed_emergency_run(job_id, content_text):
                        try:
                            delay = float(os.environ.get("EMERGENCY_DELAY_SEC", "1.5"))
                        except Exception:
                            delay = 1.5
                        await asyncio.sleep(delay)
                        if job_id and job_id in plan_seen:
                            return
                        steps = [
                            {"type":"tool","tool":"sysctl.launch","args":{"exe":"notepad","args":[]}},
                            {"type":"tool","tool":"win.activate_title_contains","args":{"substr":"Notepad"}},
                            {"type":"tool","tool":"win.activate_title_contains","args":{"substr":"Notepad"}},
                            {"type":"tool","tool":"clipboard.set_text","args":{"text": content_text}},
                            {"type":"tool","tool":"win.activate_title_contains","args":{"substr":"Notepad"}},
                            {"type":"tool","tool":"ui.hotkey","args":{"combo":"ctrl+v"}},
                            {"type":"tool","tool":"win.activate_title_contains","args":{"substr":"Notepad"}},
                            {"type":"tool","tool":"ui.hotkey","args":{"combo":"ctrl+v"}},
                            {"type":"tool","tool":"win.activate_title_contains","args":{"substr":"Notepad"}},
                            {"type":"tool","tool":"ui.hotkey","args":{"combo":"ctrl+v"}},
                            {"type":"tool","tool":"ui.hotkey","args":{"combo":"ctrl+a"}},
                            {"type":"tool","tool":"ui.hotkey","args":{"combo":"ctrl+c"}},
                        ]
                        plan = {"title":"Emergency Notepad Paste","steps":steps}
                        await bus.publish("task/plan", plan, sender="Main", job_id=job_id)
                        await bus.publish("task/exec", plan, sender="Main", job_id=job_id)
                    t = asyncio.create_task(_delayed_emergency_run(jid, content), name=f"emergency_notepad_wait_{jid or 'na'}")
                    if jid:
                        _emerg_pending[jid] = t
            except Exception:
                pass
    emerg_task = asyncio.create_task(_emergency_notepad_exec(), name="emergency_notepad_exec")
    _watch_task("emergency_notepad_exec", emerg_task)

    # Periodic loops
    async def _heartbeat_loop():
        try:
            period = float(os.environ.get("HEARTBEAT_SEC", "5"))
        except Exception:
            period = 5.0
        try:
            while True:
                try:
                    await bus.publish("system/heartbeat", {"ts": time.time(), "pid": os.getpid(), "src": "main"}, sender="Main")
                except Exception:
                    pass
                await asyncio.sleep(period)
        except asyncio.CancelledError:
            return

    async def _health_loop():
        try:
            period = float(os.environ.get("HEALTH_SEC", "60"))
        except Exception:
            period = 60.0
        elog = EventLog()
        cur = elog.conn.cursor()
        while True:
            try:
                try:
                    row = cur.execute("SELECT value FROM meta WHERE key='bridge.chat_last_id'").fetchone()
                    bridge_cursor = row[0] if row else None
                except Exception as e:
                    bridge_cursor = f"ERR: {e}"
                try:
                    ev_total = int(cur.execute("SELECT COUNT(*) FROM events").fetchone()[0])
                except Exception as e:
                    ev_total = f"ERR: {e}"
                try:
                    roll_total = int(cur.execute("SELECT COUNT(*) FROM rollups").fetchone()[0])
                except Exception as e:
                    roll_total = f"ERR: {e}"
                payload = {"ts": time.time(), "ok": True, "results": [
                    ("chat bridge cursor", bridge_cursor),
                    ("events total", ev_total),
                    ("rollups total", roll_total),
                ]}
                await bus.publish("system/health", payload, sender="Main")
            except Exception:
                pass
            try:
                await asyncio.sleep(period)
            except asyncio.CancelledError:
                break

    async def _resummarize_loop():
        try:
            period = float(os.environ.get("RESUMMARIZE_SEC", "300"))
        except Exception:
            period = 300.0
        try:
            while True:
                try:
                    await bus.publish("log/resummarize", {"hint": "periodic"}, sender="Main")
                except Exception:
                    pass
                await asyncio.sleep(period)
        except asyncio.CancelledError:
            return

    hb_task = asyncio.create_task(_heartbeat_loop(), name="heartbeat_loop")
    health_task = asyncio.create_task(_health_loop(), name="health_loop")
    resum_task = asyncio.create_task(_resummarize_loop(), name="resummarize_loop")
    _watch_task("heartbeat_loop", hb_task)
    _watch_task("health_loop", health_task)
    _watch_task("resummarize_loop", resum_task)

    # Start agents
    agents = [
        CommsAgent("AI-1:Comms", bus, llm, memory, tools),
        BrainAgent("AI-2:Brain", bus, llm, memory, tools),
        WorkerAgent("AI-3:Worker", bus, llm, memory, tools),
        TesterAgent("AI-4:Tester", bus, llm, memory, tools),
        LoggerAgent("AI-5:Logger", bus, llm, memory, tools),
    ]
    if HAS_AUTOFIX:
        agents.append(AutofixAgent("AI-6:Autofix", bus, llm, memory, tools))

    agent_tasks: List[asyncio.Task] = []
    for a in agents:
        t = asyncio.create_task(a.run(), name=a.name)
        _watch_task(a.name, t)
        agent_tasks.append(t)

    await asyncio.sleep(0)

    headless = (os.environ.get("ECOSYS_HEADLESS", "").strip().lower() in ("1", "true", "yes"))
    try:
        if headless:
            await bus.publish("ui/print", {"text": "[Main] Headless mode: running service loops only."}, sender="Main")
            try:
                stop_after = float(os.environ.get("STOP_AFTER_SEC", "0"))
            except Exception:
                stop_after = 0.0
            if stop_after > 0:
                await asyncio.sleep(stop_after)
            else:
                await asyncio.Event().wait()
        else:
            await input_loop(bus, llm, tools, memory)
    finally:
        for t in agent_tasks + ui_tasks + [rec_task, rot_task, hb_task, health_task, resum_task, emerg_task, ctrl_task, chat_task]:
            try:
                t.cancel()
            except Exception:
                pass
        await asyncio.gather(*agent_tasks, *ui_tasks, rec_task, rot_task, hb_task, health_task, resum_task, emerg_task, ctrl_task, chat_task, return_exceptions=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass





