import sys, os
# Avoid local module shadowing stdlib (e.g., tools/http.py vs stdlib http package)
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if THIS_DIR in sys.path:
    try:
        sys.path.remove(THIS_DIR)
    except Exception:
        pass

import argparse, json, hashlib, requests

def _ok(**k):  return json.dumps({'ok': True, **k}, ensure_ascii=False)
def _err(e, **k): return json.dumps({'ok': False, 'error': str(e), **k}, ensure_ascii=False)

def sha256_bytes(b):
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def ensure_dir(p):
    d = os.path.dirname(p)
    if d and not os.path.isdir(d): os.makedirs(d, exist_ok=True)

def cmd_download(a):
    try:
        url = a.url; out = a.out
        if not url or not out: return _err('need --url and --out', action='download')
        ensure_dir(out)
        timeout = float(a.timeout or 30)
        r = requests.get(url, headers={'User-Agent':'Mozilla/5.0'}, timeout=timeout)
        r.raise_for_status()
        data = r.content or b''
        with open(out, 'wb') as f: f.write(data)
        return _ok(action='download', url=url, out=out, bytes=len(data), sha256=sha256_bytes(data), status=r.status_code)
    except Exception as e:
        return _err(e, action='download', url=url if 'url' in locals() else None, out=out if 'out' in locals() else None)

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    d = sub.add_parser('download'); d.add_argument('--url'); d.add_argument('--out'); d.add_argument('--timeout', type=float); d.set_defaults(func=cmd_download)
    a = ap.parse_args()
    try: print(a.func(a))
    except Exception as e: print(_err(e, action='unknown'))

if __name__=='__main__': main()
