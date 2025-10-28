# Ensure fx.convert alias is available via ToolRegistry
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.tools import REGISTRY

def test_fx_convert_alias_registered():
    avail = REGISTRY.available()
    assert "currency.convert" in avail
    assert "fx.convert" in avail
