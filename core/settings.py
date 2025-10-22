from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Dict, Any

# Uses stdlib tomllib (Py3.11+) if config.toml exists; otherwise sane defaults.
try:
    import tomllib  # Python 3.11
except Exception:  # pragma: no cover
    tomllib = None  # We'll just ignore TOML and use defaults

DEFAULT_ROOT = "C:/bots/ecosys"

@dataclass
class Settings:
    paths: Dict[str, str] = field(default_factory=lambda: {
        "root": DEFAULT_ROOT,
        "memory": os.path.join(DEFAULT_ROOT, "memory"),
        "logs": os.path.join(DEFAULT_ROOT, "logs"),
        "workspace": os.path.join(DEFAULT_ROOT, "workspace"),
    })
    llm: Dict[str, Any] = field(default_factory=dict)
    extras: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def load(config_path: str | None = None) -> "Settings":
        root = DEFAULT_ROOT
        llm = {}
        extras = {}

        # Decide config path
        cfg = config_path or os.path.join(DEFAULT_ROOT, "config.toml")
        if tomllib and os.path.exists(cfg):
            try:
                with open(cfg, "rb") as f:
                    data = tomllib.load(f) or {}
                root = data.get("paths", {}).get("root", root)
                llm = data.get("llm", {}) or {}
                extras = {k: v for k, v in data.items() if k not in ("paths", "llm")}
            except Exception:
                # Fall back to defaults if parsing fails
                pass

        paths = {
            "root": root,
            "memory": os.path.join(root, "memory"),
            "logs": os.path.join(root, "logs"),
            "workspace": os.path.join(root, "workspace"),
        }
        return Settings(paths=paths, llm=llm, extras=extras)
