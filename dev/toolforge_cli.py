import json, argparse
from pathlib import Path
from toolforge import ToolForge

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--inbox', default=None)
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[1]
    tf = ToolForge(root)
    if args.inbox:
        tf.cfg.inbox_dir = str((root / args.inbox).resolve())
    out = tf.run_once()
    print(json.dumps(out))

if __name__ == '__main__':
    main()
