# C:\bots\ecosys\tools\gittools.py
from __future__ import annotations
import os, shutil, subprocess, shlex
from typing import Dict, Any, Optional

def _run(cmd: str, cwd: Optional[str] = None, timeout: int = 120):
    p = subprocess.run(cmd, cwd=cwd, shell=True, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    return p.returncode, p.stdout, p.stderr

def _git_exe() -> Optional[str]:
    """
    Find git.exe. Priority: env -> common paths -> PATH.
    Returns a quoted absolute path or None.
    """
    env_git = os.environ.get("GIT_PYTHON_GIT_EXECUTABLE")
    if env_git and os.path.isfile(env_git):
        return f'"{env_git}"'
    for c in [
        r"C:\Program Files\Git\bin\git.exe",
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files (x86)\Git\bin\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe",
    ]:
        if os.path.isfile(c):
            return f'"{c}"'
    which = shutil.which("git")
    if which:
        return f'"{which}"'
    return None

def _run_git(args: str, cwd: Optional[str] = None, timeout: int = 120):
    exe = _git_exe()
    if not exe:
        return 127, "", ("git executable not found. Install Git for Windows, or set "
                         "env GIT_PYTHON_GIT_EXECUTABLE to the full path of git.exe")
    return _run(f"{exe} {args}", cwd=cwd, timeout=timeout)

def init(path: str) -> Dict[str, Any]:
    os.makedirs(path, exist_ok=True)
    rc, out, err = _run_git(f'-C "{path}" init')
    return {"ok": rc == 0, "stdout": out, "stderr": err, "rc": rc}

def status(path: str) -> Dict[str, Any]:
    # Gracefully handle non-repo case (rc 128) as non-fatal with a note
    rc, out, err = _run_git(f'-C "{path}" status --porcelain=v1 -b')
    if rc == 128 and "not a git repository" in (err or "").lower():
        return {"ok": True, "note": f"not a git repository: {path}", "stdout": "", "stderr": err, "rc": rc}
    return {"ok": rc == 0, "stdout": out, "stderr": err, "rc": rc}

def clone(url: str, path: str) -> Dict[str, Any]:
    if os.path.exists(path) and os.listdir(path):
        return {"ok": False, "error": f"path exists and not empty: {path}"}
    rc, out, err = _run_git(f'clone {shlex.quote(url)} "{path}"')
    return {"ok": rc == 0, "stdout": out, "stderr": err, "rc": rc}

def pull(path: str) -> Dict[str, Any]:
    rc, out, err = _run_git(f'-C "{path}" pull --ff-only')
    return {"ok": rc == 0, "stdout": out, "stderr": err, "rc": rc}

def commit(path: str, message: str) -> Dict[str, Any]:
    rc1, out1, err1 = _run_git(f'-C "{path}" add -A')
    if rc1 != 0:
        return {"ok": False, "stdout": out1, "stderr": err1, "rc": rc1}
    rc2, out2, err2 = _run_git(f'-C "{path}" commit -m {shlex.quote(message)}')
    return {"ok": rc2 == 0, "stdout": out2, "stderr": err2, "rc": rc2}

def push(path: str, remote: str = "origin", branch: str = "main") -> Dict[str, Any]:
    rc, out, err = _run_git(f'-C "{path}" push {remote} {branch}')
    return {"ok": rc == 0, "stdout": out, "stderr": err, "rc": rc}
