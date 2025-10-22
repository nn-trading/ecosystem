# dev/git_add.py
import os, sys, json, subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def main():
    os.chdir(ROOT)
    paths = sys.argv[1:]
    if not paths:
        print(json.dumps({'error': 'usage: python dev/git_add.py <paths...>'}, ensure_ascii=True))
        sys.exit(2)
    # Use arg list to avoid Windows shell quoting pitfalls
    cmd = ["git", "add"] + paths
    proc = subprocess.run(cmd)
    rc = proc.returncode
    print(json.dumps({'cmd': ' '.join(cmd), 'exit': rc}, ensure_ascii=True))
    sys.exit(rc)

if __name__ == '__main__':
    main()
