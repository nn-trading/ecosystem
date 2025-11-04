# ASCII-only chat summarizer: maintain rolling summary and exact tail
from __future__ import annotations
import sys, json, time
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "chat_memory.yaml"
ASCII_KW = dict(encoding="ascii", errors="ignore")

DEFAULTS = {
    "transcript_path": "reports\\chat\\transcript.jsonl",
    "exact_tail_path": "reports\\chat\\exact_tail.jsonl",
    "summary_path": "reports\\chat\\summary_rolling.md",
    "state_path": "reports\\chat\\state.json",
    "memory_path": "reports\\chat\\memory.json",
    "keep_exact_n": 200,
    "rollup_every_msgs": 100,
    "rollup_interval_sec": 120,
}


def load_cfg() -> dict:
    cfg = dict(DEFAULTS)
    if CFG.exists() and yaml is not None:
        try:
            data = yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}
            if isinstance(data, dict):
                cfg.update(data)
        except Exception:
            pass
    return cfg


def path(p):
    return ROOT / str(p)


def read_jsonl(p: Path) -> list[dict]:
    items = []
    try:
        with open(p, "r", **ASCII_KW) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except Exception:
                    pass
    except FileNotFoundError:
        return []
    except Exception:
        return items
    return items


def write_json_ascii(path: Path, obj) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", **ASCII_KW) as f:
            json.dump(obj, f, ensure_ascii=True, separators=(",", ":"))
            f.write("\n")
    except Exception:
        pass


def write_text_ascii(path: Path, text: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", **ASCII_KW) as f:
            f.write(text)
            if not text.endswith("\n"):
                f.write("\n")
    except Exception:
        pass


def summarize_messages(msgs: list[dict], max_len: int = 1500) -> str:
    # Simple heuristic summarizer (no external API):
    # - keep first and last few lines; include counts
    lines = []
    n = len(msgs)
    lines.append(f"Summary: {n} messages")
    def fmt(m):
        role = (m.get("role") or "").strip()
        text = (m.get("text") or "").strip()
        text = text.replace("\n", " ")
        if len(text) > 160:
            text = text[:157] + "..."
        return f"- {role}: {text}"
    head = msgs[:3]
    tail = msgs[-3:]
    for m in head:
        lines.append(fmt(m))
    if n > 6:
        lines.append(f"... {n-6} more ...")
    for m in tail:
        lines.append(fmt(m))
    s = "\n".join(lines)
    if len(s) > max_len:
        s = s[:max_len]
    return s


def run_once(cfg: dict) -> dict:
    transcript = path(cfg.get("transcript_path"))
    exact_tail = path(cfg.get("exact_tail_path"))
    summary_path = path(cfg.get("summary_path"))
    state_path = path(cfg.get("state_path"))
    memory_path = path(cfg.get("memory_path"))
    keep_n = int(cfg.get("keep_exact_n", 200))

    msgs = read_jsonl(transcript)
    if not msgs:
        return {"ok": True, "messages": 0, "skipped": True}

    # maintain exact tail
    tail = msgs[-keep_n:]
    try:
        exact_tail.parent.mkdir(parents=True, exist_ok=True)
        with open(exact_tail, "w", **ASCII_KW) as f:
            for m in tail:
                f.write(json.dumps(m, ensure_ascii=True))
                f.write("\n")
    except Exception:
        pass

    # rolling summary
    summary = summarize_messages(msgs)
    write_text_ascii(summary_path, summary)

    # state + memory sketch
    state = {"last_ts": tail[-1].get("ts") if tail else None, "count": len(msgs)}
    write_json_ascii(state_path, state)

    memory = {"entities": [], "facts": [], "notes": summary.split("\n")[:10]}
    write_json_ascii(memory_path, memory)

    return {"ok": True, "messages": len(msgs), "tail": len(tail)}


def loop(cfg: dict) -> int:
    interval = int(cfg.get("rollup_interval_sec", 120))
    last = 0
    while True:
        try:
            res = run_once(cfg)
            last = time.time()
        except KeyboardInterrupt:
            return 130
        except Exception:
            pass
        time.sleep(interval)


def main() -> int:
    cfg = load_cfg()
    if len(sys.argv) >= 2 and sys.argv[1] == "loop":
        return loop(cfg)
    else:
        run_once(cfg)
        return 0

if __name__ == "__main__":
    raise SystemExit(main())
