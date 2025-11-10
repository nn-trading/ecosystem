import argparse, json, subprocess, sys, time, os

def _ok(**k):  return json.dumps({"ok": True, **k}, ensure_ascii=False)
def _err(e, **k): return json.dumps({"ok": False, "error": str(e), **k}, ensure_ascii=False)

def cmd_open(a):
    try:
        if a.path:
            cmd = ['powershell','-NoProfile','-ExecutionPolicy','Bypass','-Command',
                   f"Start-Process -FilePath '{a.path}'" + (f" -ArgumentList '{a.args}'" if a.args else '')]
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            return _ok(action='open', path=a.path, args=a.args or '')
        elif a.name:
            subprocess.Popen([a.name], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            return _ok(action='open', name=a.name)
        else:
            return _err('provide --path or --name', action='open')
    except Exception as e:
        return _err(e, action='open')

def cmd_close(a):
    try:
        if a.pid:
            out = subprocess.run(['taskkill','/PID',str(a.pid),'/F','/T'], capture_output=True, text=True)
            return _ok(action='close', pid=a.pid, rc=out.returncode, stdout=out.stdout, stderr=out.stderr)
        elif a.name:
            out = subprocess.run(['taskkill','/IM',a.name,'/F','/T'], capture_output=True, text=True)
            return _ok(action='close', name=a.name, rc=out.returncode, stdout=out.stdout, stderr=out.stderr)
        else:
            return _err('provide --name <exe> or --pid <id>', action='close')
    except Exception as e:
        return _err(e, action='close')

def cmd_focus(a):
    try:
        import win32gui, win32con, win32process
        target = (a.title or '').lower()
        pid = int(a.pid) if a.pid else None
        hwnd_match = None
        def _enum_cb(hwnd, _):
            nonlocal hwnd_match
            if not win32gui.IsWindowVisible(hwnd): return
            title = (win32gui.GetWindowText(hwnd) or '').strip()
            if not title: return
            if target and target in title.lower():
                hwnd_match = hwnd; return
            if pid:
                try:
                    _, wpid = win32process.GetWindowThreadProcessId(hwnd)
                    if wpid == pid: hwnd_match = hwnd
                except: pass
        win32gui.EnumWindows(_enum_cb, None)
        if not hwnd_match:
            return _err('window not found', action='focus', title=a.title, pid=pid)
        try: win32gui.ShowWindow(hwnd_match, win32con.SW_RESTORE)
        except: pass
        try: win32gui.SetForegroundWindow(hwnd_match)
        except Exception:
            # minimal fallback nudge
            try:
                shell = 'powershell -NoProfile -Command "$ws=New-Object -ComObject WScript.Shell; $ws.SendKeys(\'% \' )"'
                subprocess.run(shell, shell=True)
                win32gui.SetForegroundWindow(hwnd_match)
            except: pass
        return _ok(action='focus', title=a.title, pid=pid)
    except Exception as e:
        return _err(e, action='focus')

def cmd_list(a):
    try:
        import win32gui
        wins=[]
        def _cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                t=win32gui.GetWindowText(hwnd) or ''
                if t.strip():
                    wins.append({'hwnd': hwnd, 'title': t})
        win32gui.EnumWindows(_cb, None)
        flt=(a.filter or '').lower()
        if flt:
            wins=[w for w in wins if flt in (w['title'] or '').lower()]
        return _ok(action='list', windows=wins[:200], count=len(wins))
    except Exception as e:
        return _err(e, action='list')

def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest='cmd', required=True)
    p=sub.add_parser('open');  p.add_argument('--path'); p.add_argument('--name'); p.add_argument('--args'); p.set_defaults(func=cmd_open)
    c=sub.add_parser('close'); c.add_argument('--name'); c.add_argument('--pid', type=int);                  c.set_defaults(func=cmd_close)
    f=sub.add_parser('focus'); f.add_argument('--title'); f.add_argument('--pid', type=int);                  f.set_defaults(func=cmd_focus)
    l=sub.add_parser('list');  l.add_argument('--filter');                                                    l.set_defaults(func=cmd_list)
    a=ap.parse_args()
    try: print(a.func(a))
    except Exception as e: print(_err(e, action='unknown'))
if __name__=='__main__': main()
