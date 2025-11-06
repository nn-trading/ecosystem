from policy.engine import check_action

def test_high_risk_denied_without_elevation():
    assert not check_action('apply registry change')['allowed']

def test_secret_retrieval_jit():
    from security.cred_broker_win import get_secret
    assert get_secret('WEBHOOK_TOKEN')==''
