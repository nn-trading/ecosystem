# dev/git_push.py
import os, sys, json, subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def main():
    os.chdir(ROOT)
    remote = sys.argv[1] if len(sys.argv) > 1 else 'origin'
    if len(sys.argv) > 2:
        branch = sys.argv[2]
    else:
        try:
            branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], text=True).strip()
        except Exception:
            branch = 'master'
    rc = subprocess.call(['git', 'push', remote, branch])
    print(json.dumps({'remote': remote, 'branch': branch, 'exit': rc}, ensure_ascii=True))
    sys.exit(rc)

if __name__ == '__main__':
    main()
