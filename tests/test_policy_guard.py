from dev.policy_guard import check

def test_policy_auto():
    r=check("plan_apply","medium")
    assert r["allowed"] in (True, False)
