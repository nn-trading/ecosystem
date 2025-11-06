from services.comms import notify

def test_local_notification(tmp_path):
    assert notify.local('hello')

def test_webhook_log(tmp_path):
    assert notify.webhook('default','hi')
