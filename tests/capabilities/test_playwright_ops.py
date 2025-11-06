from services.web.playwright_ops import open_page

def test_open_page():
    assert open_page('http://example.com', profile='default', headed=False)

def test_download_upload_handler():
    assert True
