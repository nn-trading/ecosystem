from pathlib import Path

def index_path(p: str):
    path = Path(p)
    if not path.exists():
        return 0
    n=0
    for f in path.rglob('*'):
        if f.is_file():
            n+=1
    return n
