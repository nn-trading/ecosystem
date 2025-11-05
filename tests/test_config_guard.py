# tests/test_config_guard.py
from pathlib import Path
from dev.config_guard import load_cfg

def test_defaults_apply():
    cfg, problems = load_cfg("missing.yaml", {"foo":"bar"})
    assert cfg.get("foo")=="bar"
