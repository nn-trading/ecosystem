# dev/redact.py
from __future__ import annotations
import re, sys
PATTERNS=[
    (re.compile(r"(OPENAI|ANTHROPIC|MISTRAL|AZURE)[A-Z0-9_]*\s*[:=]\s*([\"']?)([A-Za-z0-9_\-\.\|]{12,})(\2)"), r"\1=***REDACTED***"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "***REDACTED***"),
]

def sanitize(s:str)->str:
    for rx,rep in PATTERNS: s=rx.sub(rep, s)
    return s

if __name__=="__main__":
    data=sys.stdin.read()
    sys.stdout.write(sanitize(data))
