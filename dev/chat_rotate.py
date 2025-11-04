import os, time, shutil

transcript = os.path.join('reports', 'chat', 'transcript.jsonl')
archive_dir = os.path.join('reports', 'chat', 'archive')
max_lines = 200000
max_bytes = 10485760  # 10 MB
interval_sec = 60

def ensure_paths():
    try:
        os.makedirs(os.path.dirname(transcript), exist_ok=True)
        os.makedirs(archive_dir, exist_ok=True)
        if not os.path.exists(transcript):
            open(transcript, 'w', encoding='ascii', errors='ignore').close()
    except Exception:
        pass

def needs_rotate(path):
    try:
        size_ok = os.path.getsize(path) > max_bytes
    except Exception:
        size_ok = False
    line_ok = False
    try:
        cnt = 0
        with open(path, 'r', encoding='ascii', errors='ignore') as f:
            for cnt, _ in enumerate(f, 1):
                if cnt > max_lines:
                    line_ok = True
                    break
    except Exception:
        line_ok = False
    return size_ok or line_ok

def rotate():
    try:
        ts = time.strftime('%Y%m%d_%H%M%S')
        base = 'transcript_%s.jsonl' % ts
        dst = os.path.join(archive_dir, base)
        # Move then recreate
        try:
            shutil.move(transcript, dst)
        except Exception:
            # best-effort copy+truncate fallback
            try:
                shutil.copy2(transcript, dst)
            except Exception:
                pass
            try:
                open(transcript, 'w', encoding='ascii', errors='ignore').close()
            except Exception:
                pass
        # Ensure new empty file exists
        try:
            open(transcript, 'a', encoding='ascii', errors='ignore').close()
        except Exception:
            pass
    except Exception:
        pass

def main():
    ensure_paths()
    while True:
        try:
            if os.path.exists(transcript) and needs_rotate(transcript):
                rotate()
        except Exception:
            pass
        time.sleep(interval_sec)

if __name__ == '__main__':
    main()
