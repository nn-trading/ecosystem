from router.model_router import route
from router.referee import dual_run_referee

def test_routing_policy_applied():
    assert route('summarize x')['policy']=='fast'

def test_dual_run_referee_gate():
    assert dual_run_referee('apply registry change', dual=True)['decision']=='allow'
