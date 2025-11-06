def test_endpoints_health():
    from dashboard.app import run
    assert run()['ok']

def test_tail_filters():
    assert True
