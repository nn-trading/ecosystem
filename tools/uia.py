# C:\bots\ecosys\tools\uia.py
from __future__ import annotations
import subprocess
from typing import Any, Dict

_PS_GET = r'''
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$el = [System.Windows.Automation.AutomationElement]::FocusedElement
if ($null -eq $el) { "no-focus"; return }
$p = $null
if ($el.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$p)) {
  $val = $p.Current.Value
  if ($null -eq $val) { $val = "" }
  "ok:" + $val
} else {
  "no-value"
}
'''

_PS_SET = r'''
param([string]$Text = "")
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$el = [System.Windows.Automation.AutomationElement]::FocusedElement
if ($null -eq $el) { "no-focus"; return }
$p = $null
if ($el.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$p)) {
  $p.SetValue($Text)
  "ok"
} else {
  "no-value"
}
'''

def focused_get_value() -> Dict[str, Any]:
    c = subprocess.run(["powershell","-NoProfile","-Sta","-Command", _PS_GET],
                       capture_output=True, text=True, encoding="utf-8")
    out = (c.stdout or "").strip()
    if out.startswith("ok:"):
        return {"ok": True, "text": out[3:]}
    if out == "no-focus":
        return {"ok": False, "error": "no_focus"}
    if out == "no-value":
        return {"ok": False, "error": "no_value_pattern"}
    return {"ok": False, "error": out or c.stderr or f"exit {c.returncode}"}

def focused_set_value(text: str) -> Dict[str, Any]:
    c = subprocess.run(["powershell","-NoProfile","-Sta","-Command", _PS_SET, "-Text", text],
                       capture_output=True, text=True, encoding="utf-8")
    out = (c.stdout or "").strip()
    if out == "ok":
        return {"ok": True}
    if out == "no-focus":
        return {"ok": False, "error": "no_focus"}
    if out == "no-value":
        return {"ok": False, "error": "no_value_pattern"}
    return {"ok": False, "error": out or c.stderr or f"exit {c.returncode}"}

def register(tools) -> None:
    tools.add("uia.focused_get_value", focused_get_value, desc="Read text value of the focused control via UI Automation")
    tools.add("uia.focused_set_value", focused_set_value, desc="Set text value of the focused control via UI Automation (ValuePattern)")
