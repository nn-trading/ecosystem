# ASCII-only updater to mark RC-PLAN done in logs/tasks.json
import json, time
from pathlib import Path

def main() -> int:
    p = Path(r'C:\bots\ecosys\logs\tasks.json')
    try:
        data = json.loads(p.read_text(encoding='ascii', errors='ignore') or '{}')
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    sess = data.get('session_tasks') or []
    if not isinstance(sess, list):
        sess = []
    found = False
    for t in sess:
        try:
            if str(t.get('id')) == 'RC-PLAN':
                t['status'] = 'done'
                found = True
        except Exception:
            pass
    if not found:
        sess.append({
            'id': 'RC-PLAN',
            'title': 'Reality Check plan across 12 capabilities',
            'status': 'done',
            'notes': 'closed ' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
        })
    data['session_tasks'] = sess
    try:
        data['updated_ts'] = int(time.time())
    except Exception:
        pass
    p.write_text(json.dumps(data, ensure_ascii=True, indent=2) + '\n', encoding='ascii', errors='ignore')
    print('RC-PLAN marked done')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
