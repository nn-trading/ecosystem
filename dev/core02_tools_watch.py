import time, json, os
from pathlib import Path
from toolforge import ToolForge

# Simple watcher loop: polls inbox every 5s

def main():
    root = Path(__file__).resolve().parents[1]
    tf = ToolForge(root)
    interval = 5
    while True:
        try:
            res = tf.run_once()
            print(json.dumps(res))
        except Exception as e:
            print('{"ok": false, "error": "'+str(e).replace('"','\"')+'"}')
        time.sleep(interval)

if __name__ == '__main__':
    main()
