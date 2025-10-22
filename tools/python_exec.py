from __future__ import annotations
import subprocess, tempfile, sys, textwrap

def run(code: str, danger: bool = False) -> dict:
    if not danger:
        return {"ok": False, "error": "danger_mode off: python execution disabled"}
    if not code.strip():
        return {"ok": False, "error": "no code provided"}
    # Write to temp file for Windows reliability
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(textwrap.dedent(code))
        path = f.name
    try:
        cp = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=600)
        return {"ok": cp.returncode == 0, "code": cp.returncode, "stdout": cp.stdout, "stderr": cp.stderr, "path": path}
    except Exception as e:
        return {"ok": False, "error": str(e), "path": path}
