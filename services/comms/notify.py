from pathlib import Path

def local(text: str):
    p = Path("runs")
    p.mkdir(exist_ok=True)
    (p/"local_notify.log").write_text(str(text), encoding="ascii", errors="ignore")
    return True

def webhook(name: str, text: str):
    p = Path("runs")
    p.mkdir(exist_ok=True)
    (p/f"webhook_{name}.log").write_text(str(text), encoding="ascii", errors="ignore")
    return True
