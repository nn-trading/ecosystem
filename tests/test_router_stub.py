from dev.router_stub import choose

def test_choose_defaults():
    assert choose("unknown") in ("gpt-4o-mini","gpt-5")
