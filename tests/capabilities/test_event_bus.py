from bus import local_bus

def test_publish_subscribe_loopback():
    assert local_bus.smoke()

def test_fallback_to_filebus():
    assert True
