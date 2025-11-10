import argparse, json

def _ok(**k):  import json as j; return j.dumps({'ok': True, **k}, ensure_ascii=False)

def _err(e, **k): import json as j; return j.dumps({'ok': False, 'error': str(e), **k}, ensure_ascii=False)

def cmd_press(a):
    try:
        import pyautogui, time
        keys=[k.strip() for k in (a.keys or '').split(',') if k.strip()]
        interval=float(a.interval or 0.0)
        for k in keys:
            pyautogui.press(k.lower())
            if interval: time.sleep(interval)
        return _ok(action='press', keys=keys)
    except Exception as e:
        return _err(e, action='press')

def cmd_hotkey(a):
    try:
        import pyautogui
        parts=[p.strip() for p in (a.combo or '').replace('+',' ').split() if p.strip()]
        if not parts: return _err('provide --combo like ctrl+s', action='hotkey')
        pyautogui.hotkey(*[p.lower() for p in parts], interval=float(a.interval or 0.0))
        return _ok(action='hotkey', combo=parts)
    except Exception as e:
        return _err(e, action='hotkey')

def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest='cmd', required=True)
    p=sub.add_parser('press');  p.add_argument('--keys');   p.add_argument('--interval', type=float); p.set_defaults(func=cmd_press)
    h=sub.add_parser('hotkey'); h.add_argument('--combo');  h.add_argument('--interval', type=float); h.set_defaults(func=cmd_hotkey)
    a=ap.parse_args()
    try: print(a.func(a))
    except Exception as e: print(_err(e, action='unknown'))
if __name__=='__main__': main()
