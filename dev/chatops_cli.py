# dev/chatops_cli.py (ASCII-only)
import sys, json
from pathlib import Path
IN = Path(__file__).resolve().parents[1]/"reports/intents_in.jsonl"
def submit(text:str):
    IN.parent.mkdir(parents=True, exist_ok=True)
    with IN.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"text": text}, ensure_ascii=True)+"\n")
    print('{"ok":true}')
def main():
    if len(sys.argv)<2:
        print('Usage: python dev\\chatops_cli.py "your goal sentence"'); return
    submit(" ".join(sys.argv[1:]))
if __name__=="__main__": main()
