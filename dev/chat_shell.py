# ASCII-only chat shell that records stdin/out to transcript.jsonl
from __future__ import annotations
import sys, json, time
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # fallback paths set below

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "chat_memory.yaml"
DEFAULTS = {
    "transcript_path": "reports\\chat\\transcript.jsonl",
    "exact_tail_path": "reports\\chat\\exact_tail.jsonl",
    "summary_path": "reports\\chat\\summary_rolling.md",
    "state_path": "reports\\chat\\state.json",
    "memory_path": "reports\\chat\\memory.json",
    "keep_exact_n": 200,
}

ASCII_KW = dict(encoding="ascii", errors="ignore")

def load_cfg() -> dict:
    cfg = dict(DEFAULTS)
    if CFG.exists() and yaml is not None:
        try:
            data = yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}
            if isinstance(data, dict):
                cfg.update({k: v for k, v in data.items() if k in DEFAULTS or k.endswith("_path")})
        except Exception:
            pass
    return cfg


def ensure_parent(p: Path) -> None:
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def write_jsonl(path: Path, obj: dict) -> None:
    try:
        ensure_parent(path)
        with open(path, "a", **ASCII_KW) as f:
            f.write(json.dumps(obj, ensure_ascii=True))
            f.write("\n")
    except Exception:
        pass


def main() -> int:
    cfg = load_cfg()
    transcript = ROOT / str(cfg.get("transcript_path"))
    ensure_parent(transcript)

    print("Chat shell ready. Type lines; Ctrl+C to exit.")
    try:
        for line in sys.stdin:
            s = line.rstrip("\n")
            ts = time.time()
            write_jsonl(transcript, {"ts": ts, "role": "user", "text": s})
            # Echo back for demonstration; real integration would call a model
            reply = "echo: " + s
            write_jsonl(transcript, {"ts": time.time(), "role": "assistant", "text": reply})
            try:
                sys.stdout.write(reply + "\n")
                sys.stdout.flush()
            except Exception:
                pass
    except KeyboardInterrupt:
        return 130
    except Exception:
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
