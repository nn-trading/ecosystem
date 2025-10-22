# dev/git_commit_msg.py
import os, sys, json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

USAGE = "usage: python dev/git_commit_msg.py <msg_file>"

def main():
    os.chdir(ROOT)
    if len(sys.argv) < 2:
        print(json.dumps({'error': USAGE}, ensure_ascii=True))
        sys.exit(2)
    msg_file = sys.argv[1]
    try:
        with open(msg_file, 'r', encoding='utf-8', errors='ignore') as f:
            msg = f.read().strip()
    except Exception as e:
        print(json.dumps({'error': f'read {msg_file} failed: {e}'}, ensure_ascii=True))
        sys.exit(2)
    if not msg:
        print(json.dumps({'error': 'empty commit message'}, ensure_ascii=True))
        sys.exit(2)
    import subprocess
    # Ensure identity configured
    try:
        subprocess.check_call(['git', 'config', 'user.name'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        subprocess.call(['git', 'config', 'user.name', 'openhands'])
    try:
        subprocess.check_call(['git', 'config', 'user.email'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        subprocess.call(['git', 'config', 'user.email', 'openhands@all-hands.dev'])
    full_msg = msg + "\n\nCo-authored-by: openhands <openhands@all-hands.dev>"
    rc = subprocess.call(['git', 'commit', '-a', '-m', full_msg])
    print(json.dumps({'exit': rc}, ensure_ascii=True))
    sys.exit(rc)

if __name__ == '__main__':
    main()
