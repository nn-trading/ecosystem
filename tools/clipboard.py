# C:\bots\ecosys\tools\clipboard.py
from future import annotations
import subprocess
from typing import Any, Dict

def _ps_get_clip() -> Dict[str, Any]:
    try:
        c = subprocess.run(
            ["powershell","-Sta","-NoProfile","-Command","[Console]::OutputEncoding=[Text.UTF8Encoding]::UTF8; Get-Clipboard -Raw"],
            capture_output=True, text=True, encoding="utf-8"
        )
        if c.returncode == 0:
            txt = c.stdout.rstrip("\r\n")
            return {"ok": True, "text": txt}
        return {"ok": False, "error": c.stderr or f"ps exited {c.returncode}"}
    except Exception as e:
        return {"ok": False, "error": f"{e.class.name}: {e}"}

def _ps_set_clip(text: str) -> Dict[str, Any]:
    try:
        if text == "":
            c = subprocess.run(
                ["powershell","-Sta","-NoProfile","-Command","Set-Clipboard -Value ''"],
                capture_output=True, text=True, encoding="utf-8"
            )
        else:
            c = subprocess.run(
                ["powershell","-Sta","-NoProfile","-Command","Set-Clipboard -Value ([Console]::In.ReadToEnd())"],
                input=text, capture_output=True, text=True, encoding="utf-8"
            )
        if c.returncode == 0:
            return {"ok": True}
        return {"ok": False, "error": c.stderr or f"ps exited {c.returncode}"}
    except Exception as e:
        return {"ok": False, "error": f"{e.class.name}: {e}"}

def get_text() -> Dict[str, Any]:
    return _ps_get_clip()

def set_text(text: str) -> Dict[str, Any]:
    return _ps_set_clip(text)

def clear() -> Dict[str, Any]:
    return _ps_set_clip("")

def register(tools) -> None:
    tools.add("clipboard.get_text", get_text, desc="Get text from clipboard")
    tools.add("clipboard.set_text", set_text, desc="Set text to clipboard")
    tools.add("clipboard.clear",    clear,    desc="Clear clipboard (empty string)")
