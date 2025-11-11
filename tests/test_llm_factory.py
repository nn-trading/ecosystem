import yaml
from core.llm_provider import load_provider
from pathlib import Path

def test_llm_provider_loads_from_config():
    cfg = yaml.safe_load(Path('config/llm.yaml').read_text())
    prov = str(cfg.get('provider'))
    model = str(cfg.get('model'))
    p = load_provider(prov, model)
    out = p.complete("ping")
    assert isinstance(out, str)
