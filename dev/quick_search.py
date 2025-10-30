import sys, json, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from memory.eventlog import EventLog

def main():
    q = sys.argv[1] if len(sys.argv) > 1 else 'system/heartbeat'
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    el = EventLog()
    rows = el.search(q, n)
    print(json.dumps({'q': q, 'n': n, 'rows': rows}, ensure_ascii=True))

if __name__ == '__main__':
    main()
