from pathlib import Path


def sweep(runs_dir: str = 'runs', keep: int = 10) -> int:
    p = Path(runs_dir)
    if not p.exists():
        return 0
    ds = sorted(
        [d for d in p.iterdir() if d.is_dir() and d.name.startswith('cap_')],
        key=lambda d: d.name,
    )
    if len(ds) <= keep:
        return 0
    to_rm = ds[:-keep]
    n = 0
    for d in to_rm:
        try:
            # remove files then dirs
            for sub in sorted(d.rglob('*'), reverse=True):
                try:
                    if sub.is_file():
                        sub.unlink()
                    elif sub.is_dir():
                        sub.rmdir()
                except Exception:
                    pass
            d.rmdir()
            n += 1
        except Exception:
            pass
    return n


if __name__ == '__main__':
    import sys

    runs_dir = 'runs'
    keep = 10
    # optional CLI: python snapshot_gc.py [runs_dir] [keep]
    if len(sys.argv) > 1 and sys.argv[1] not in ('', 'sweep'):
        runs_dir = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            keep = int(sys.argv[2])
        except Exception:
            keep = 10
    removed = sweep(runs_dir, keep)
    print(f'removed {removed}')

