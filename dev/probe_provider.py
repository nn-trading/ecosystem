import os, sys, json
from pathlib import Path
# Ensure repo root on sys.path for 'core.*' imports when running from dev/
ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from core.llm_provider import provider_factory

def run_once():
    p = provider_factory()
    out = p.complete("Reply ONLY with: ECOSYSTEM-LIVE")
    print(out)

if __name__ == "__main__":
    run_once()
