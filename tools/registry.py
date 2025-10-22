from __future__ import annotations
import winreg

ROOTS = {
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
    "HKCR": winreg.HKEY_CLASSES_ROOT,
    "HKU":  winreg.HKEY_USERS,
    "HKCC": winreg.HKEY_CURRENT_CONFIG,
}

TYPES = {
    "SZ": winreg.REG_SZ,
    "DWORD": winreg.REG_DWORD,
    "QWORD": winreg.REG_QWORD,
    "EXPAND_SZ": winreg.REG_EXPAND_SZ,
}

def query(root: str, path: str, name: str) -> dict:
    try:
        key = winreg.OpenKey(ROOTS[root], path)
        val, typ = winreg.QueryValueEx(key, name)
        winreg.CloseKey(key)
        return {"ok": True, "value": val, "type": typ}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def set_value(root: str, path: str, name: str, typ: str, value, danger: bool=False) -> dict:
    if not danger:
        return {"ok": False, "error": "danger_mode off for registry writes"}
    try:
        key = winreg.CreateKey(ROOTS[root], path)
        winreg.SetValueEx(key, name, 0, TYPES[typ], value)
        winreg.CloseKey(key)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
