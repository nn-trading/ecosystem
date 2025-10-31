import os, sys, json, time
from pathlib import Path

# Ensure we can import project modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.tools import REGISTRY as ToolsRegistry  # type: ignore
from memory.logger_db import get_logger_db  # type: ignore

ASCII_JSON_KW = dict(ensure_ascii=True, separators=(",", ":"))

def write_json_ascii(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="ascii", errors="ignore") as f:
        json.dump(data, f, **ASCII_JSON_KW)
        f.write("\n")


def write_text_ascii(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="ascii", errors="ignore") as f:
        f.write(text)
        if not text.endswith("\n"):
            f.write("\n")


def tracer(topic: str, payload: dict) -> None:
    try:
        get_logger_db().log_tool_event(topic, payload)
    except Exception:
        pass
    # Append a tiny breadcrumb for quick inspection
    try:
        with open(PROOF_DIR / "last_tool_event.txt", "a", encoding="ascii", errors="ignore") as f:
            line = json.dumps({"topic": topic, "tool": (payload or {}).get("tool")}, ensure_ascii=True)
            f.write(line + "\n")
    except Exception:
        pass


REPO = Path(__file__).resolve().parent.parent
PROOF_DIR = REPO / "logs" / "proofs"


def set_env_defaults() -> None:
    os.environ.setdefault("AGENT_DANGER_MODE", "1")
    os.environ.setdefault("ECOSYS_HEADLESS", "1")
    os.environ.setdefault("OMEGA_PROOFS", "1")
    os.environ.setdefault("AUTOACQUIRE_MAX", "3")
    os.environ.setdefault("STOP_AFTER_SEC", "0")
    os.environ.setdefault("ASCII_STRICT", "1")


def runtime_unblock(tools) -> dict:
    out = {}
    try:
        pid = os.getpid()
        before = tools.call("runtime.children", parent_pid=pid, recursive=True)
        out["children_before"] = before
        kill = tools.call("runtime.kill_children", parent_pid=pid)
        out["kill_children"] = kill
        after = tools.call("runtime.children", parent_pid=pid, recursive=True)
        out["children_after"] = after
        return {"ok": True, **out}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", **out}


def verify_tools(tools) -> dict:
    data = {}
    try:
        names = tools.available() if hasattr(tools, "available") else []
        data["names"] = list(names or [])
        try:
            from core.tools import TOOL_DESCRIPTORS as _TD  # type: ignore
            data["descriptor_keys"] = sorted(list(_TD.keys()))
        except Exception:
            data["descriptor_keys"] = []
        return {"ok": True, **data}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def audit_find_usage(tools) -> dict:
    report = {"ok": True, "findstr": None, "find_cmd": None}
    root = str(REPO)
    try:
        try:
            r1 = tools.call("repo.search", root=root, query="FINDSTR", regex=False, icase=True, max_results=400)
        except Exception as e:
            r1 = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        try:
            r2 = tools.call("repo.search", root=root, query=" FIND ", regex=False, icase=True, max_results=400)
        except Exception as e:
            r2 = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        report["findstr"] = r1
        report["find_cmd"] = r2
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    return report


def loggerdb_e2e() -> dict:
    db = get_logger_db()
    # Seed a few events and a tool call to exercise artifact capture
    try:
        db.append_event(agent="OmegaRun", type_="omega/start", payload={"note": "omega_run bootstrap"})
    except Exception:
        pass
    # Make a simple tool call to ensure tracer logs an event
    try:
        ToolsRegistry.call("fs.ls", path=str(REPO))
    except Exception:
        pass
    out = {}
    try:
        out["stats"] = db.stats()
    except Exception as e:
        out["stats_err"] = str(e)
    try:
        out["recent"] = db.recent_events(50)
    except Exception as e:
        out["recent_err"] = str(e)
    try:
        out["artifacts"] = db.recent_artifacts(50)
    except Exception as e:
        out["artifacts_err"] = str(e)
    try:
        out["top_event_types"] = db.top_event_types(10)
    except Exception as e:
        out["top_err"] = str(e)
    try:
        out["search_tool_result"] = db.retrieve("tool/result", k=20)
    except Exception as e:
        out["search_err"] = str(e)
    return out


def main() -> int:
    set_env_defaults()
    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    # Hook tracer so tool calls are logged to LoggerDB
    try:
        if hasattr(ToolsRegistry, "set_tracer"):
            ToolsRegistry.set_tracer(tracer)  # type: ignore
    except Exception:
        pass

    # Snapshot env for proofs
    env_keys = [
        "AGENT_DANGER_MODE","ECOSYS_HEADLESS","OMEGA_PROOFS","AUTOACQUIRE_MAX","STOP_AFTER_SEC","ASCII_STRICT"
    ]
    env_dump = {k: str(os.environ.get(k, "")) for k in env_keys}
    write_text_ascii(PROOF_DIR / "omega_env.txt", "\n".join([f"{k}={v}" for k, v in env_dump.items()]))

    # RUNTIME-UNBLOCK
    ru = runtime_unblock(ToolsRegistry)
    write_json_ascii(PROOF_DIR / "runtime_unblock.json", ru)

    # VERIFY-TOOLS
    vt = verify_tools(ToolsRegistry)
    write_json_ascii(PROOF_DIR / "verify_tools.json", vt)
    try:
        names = vt.get("names") or []
        write_text_ascii(PROOF_DIR / "tools_registry_names.txt", "\n".join([str(n) for n in names]))
        desc = vt.get("descriptor_keys") or []
        write_text_ascii(PROOF_DIR / "tool_descriptors_keys.txt", "\n".join([str(k) for k in desc]))
    except Exception:
        pass

    # REPLACE-FIND audit
    au = audit_find_usage(ToolsRegistry)
    write_json_ascii(PROOF_DIR / "find_usage.json", au)

    # CORE-03: LoggerDB end-to-end
    le = loggerdb_e2e()
    write_json_ascii(PROOF_DIR / "loggerdb_e2e.json", le)

    # Final banner
    summary_lines = []
    summary_lines.append("OMEGA run complete")
    summary_lines.append(f"Danger mode: {os.environ.get('AGENT_DANGER_MODE')}")
    summary_lines.append(f"Proofs dir: {PROOF_DIR}")
    write_text_ascii(PROOF_DIR / "omega_summary.txt", "\n".join(summary_lines))

    # Also print to stdout for visibility
    print("\n".join(summary_lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
