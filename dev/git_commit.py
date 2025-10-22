# dev/git_commit.py
import os, sys, json, subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def main():
    os.chdir(ROOT)
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'usage: python dev/git_commit.py "message"'}, ensure_ascii=True))
        sys.exit(2)
    msg = sys.argv[1]
    # Ensure identity configured once per repo if missing
    try:
        subprocess.check_call(['git', 'config', 'user.name'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        subprocess.call(['git', 'config', 'user.name', 'openhands'])
    try:
        subprocess.check_call(['git', 'config', 'user.email'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        subprocess.call(['git', 'config', 'user.email', 'openhands@all-hands.dev'])
    # Append co-author
    full_msg = f"{msg}\n\nCo-authored-by: openhands <openhands@all-hands.dev>"
    rc = subprocess.call(['git', 'commit', '-a', '-m', full_msg])
    print(json.dumps({'exit': rc}, ensure_ascii=True))
    sys.exit(rc)

if __name__ == '__main__':
    main()
