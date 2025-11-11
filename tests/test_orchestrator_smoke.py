import asyncio
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.orchestrator import run

@pytest.mark.asyncio
async def test_smoke_done_event(monkeypatch):
    # In CI we cannot open GUI; set environment to short-circuit worker
    if os.environ.get("CI", "").lower() in ("1","true","yes"):
        os.environ["ECOSYS_STUB_SMOKE"] = "1"
    await asyncio.wait_for(run(headless=True, smoke=True), timeout=10)
