from services.process_orchestrator import ProcessOrchestrator

def test_launch_profile():
    po = ProcessOrchestrator()
    pid = po.launch_profile('browser')
    assert pid is not None and pid > 0

def test_restart_elevated():
    po = ProcessOrchestrator()
    assert po.restart_elevated_if_needed(12345)
