from __future__ import annotations
import json, sys

def get(name:str)->dict:
    try:
        import win32cred
        cred=win32cred.CredRead(name, win32cred.CRED_TYPE_GENERIC, 0)
        return {"ok":True,"username":cred.get("UserName"),"blob":"PRESENT"}
    except Exception:
        return {"ok":False,"reason":"unavailable"}

if __name__=="__main__":
    print(json.dumps(get("ECOSYS_DEMO"), ensure_ascii=True))
