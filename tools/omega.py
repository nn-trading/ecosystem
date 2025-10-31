# C:\bots\ecosys\tools\omega.py
from __future__ import annotations
from typing import Any, Dict, Optional


def run() -> Dict[str, Any]:
    """Run dev/omega_run.main() in-process to produce proofs and LoggerDB traces.
    Returns {ok, code, proof_dir}.
    """
    try:
        from dev.omega_run import main as omega_main, PROOF_DIR  # type: ignore
    except Exception as e:
        return {"ok": False, "error": f"import error: {e.__class__.__name__}: {e}"}
    try:
        code = int(omega_main() or 0)
        return {"ok": code == 0, "code": code, "proof_dir": str(PROOF_DIR)}
    except SystemExit as se:
        try:
            code = int(se.code or 0)
        except Exception:
            code = 1
        return {"ok": code == 0, "code": code}
    except Exception as e:
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}


def register(tools) -> None:
    tools.add("omega.run", run, desc="Run dev/omega_run to produce proofs and LoggerDB traces in-process")
