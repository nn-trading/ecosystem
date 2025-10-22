# C:\bots\ecosys\main.py
from __future__ import annotations
import os, asyncio, textwrap, json, datetime, sqlite3, time
from typing import List

ASSISTANT_CONFIG_PATH = os.environ.get("ASSISTANT_CONFIG_PATH", "C:\\bots\\assistant\\config.json")

def _load_assistant_config():
    try:
        with open(ASSISTANT_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _assistant_log_path(cfg):
    log_dir = cfg.get("log_dir") or "C:\\bots\\assistant\\logs"
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
        with open(path, "a", encoding="utf-8") as f:
            line = json.dumps(obj, ensure_ascii=False) + "\n"
            f.write(line)
            try:
                db = cfg.get("memory_db") or r"C:\\bots\\assistant\\memory.db"
                con = sqlite3.connect(db)
                cur = con.cursor()
                cur.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT)")
                cur.execute("INSERT OR REPLACE INTO kv(key,value) VALUES (?,?)", ("assistant_jsonl_size", str(os.path.getsize(path))))
                cur.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, session_id TEXT, key TEXT, value TEXT)")
                cur.execute("INSERT INTO notes(ts, session_id, key, value) VALUES (?,?,?,?)", (time.time(), cfg.get("last_session") or "", "assistant_log_append", line[:500]))
                con.commit(); con.close()
            except Exception:
                pass
    except Exception:
        pass

# --- Core ---
from core.bus import EventBus
from core.llm_client import LLMClient
from core.tools import REGISTRY as ToolsRegistry   # << use the SINGLETON
from core.memory import Memory
from core.assistant_loader import AssistantLoader

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


async def ui_printer(bus: EventBus):
    async for env in bus.subscribe("ui/print"):
        payload = env.payload or {}
        text = payload.get("text") or ""
        if text:
            print(f"AI: {text}")

async def summary_printer(bus: EventBus):
    async for env in bus.subscribe("memory/summary"):
        txt = (env.payload or {}).get("text") or ""
        if txt:
            print(f"AI: [Summary] {txt}")

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
        print("GPT-5 Desktop Ecosystem ready. Type your instruction. '/status' or '/tools' or '/summary' or '/memstats' or '/model' or '/setmodel <name>' or '/resummarize' or 'exit'")
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
            cmd = parts[0]
            arg = parts[1] if len(parts) > 1 else ""
            _append_assistant_jsonl({"ts": _iso_now(), "event": "user_command", "cmd": cmd, "arg": arg})

            if cmd == "/tools":
                try:
                    avail = tools.available() if hasattr(tools, "available") else []
                except Exception:
                    avail = []
                print(f"AI: Tools: {', '.join(avail)}")
                continue
            if cmd == "/status":
                print("AI: System online. Agents running.")
                continue
            if cmd == "/memstats":
                st = memory.stats()
                pretty = "\n".join(f"- {k}: {v}" for k, v in st.items())
                print("AI: Memstats:\n" + textwrap.indent(pretty, "    "))
                continue
            if cmd == "/summary":
                await bus.publish("ui/print", {"text": "[Main] Requesting recent summary..."}, sender="Main")
                await bus.publish("task/new", {"text": "/summary (request recent summary)"}, sender="Main")
                continue
            if cmd == "/model":
                print(f"AI: Model: {getattr(llm, 'model', None)}")
                continue
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

            print(f"AI: Unknown command '{cmd}'.")
            continue

        # Normal user input -> Comms
        print(f"Me: {s}")
        await bus.publish("user/text", {"text": s}, sender="User")


async def main():
    # Assistant-level auto-resume log entry
    _append_assistant_jsonl({"ts": _iso_now(), "event": "ecosys_start", "note": "bootstrap main()"})

    bus = EventBus()
    llm = LLMClient(timeout_sec=int(os.environ.get("LLM_TIMEOUT_SEC", "45")))
    memory = Memory()
    tools = ToolsRegistry   # << IMPORTANT: this is the shared singleton with all registrations

    # Centralize tool tracing via ToolsRegistry -> publish to EventBus
    try:
        def _tools_trace(topic: str, payload: dict):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(bus.publish(topic, payload, sender="ToolsRegistry"))
            except Exception:
                pass
        if hasattr(tools, "set_tracer"):
            tools.set_tracer(_tools_trace)  # type: ignore[attr-defined]
    except Exception:
        pass

    # Start UI consumers first
    # Assistant resume context
    try:
        loader = AssistantLoader()
        await loader.publish_resume(bus)
    except Exception:
        pass

    ui_tasks: List[asyncio.Task] = []
    t1 = asyncio.create_task(ui_printer(bus), name="ui_printer")
    t2 = asyncio.create_task(summary_printer(bus), name="summary_printer")
    _watch_task("ui_printer", t1)
    _watch_task("summary_printer", t2)
    ui_tasks += [t1, t2]

    await asyncio.sleep(0)

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

    try:
        await input_loop(bus, llm, tools, memory)
    finally:
        for t in agent_tasks + ui_tasks:
            t.cancel()
        await asyncio.gather(*agent_tasks, *ui_tasks, return_exceptions=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
