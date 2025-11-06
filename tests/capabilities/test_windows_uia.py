from services.ui.windows_uia import find_by_name, click_pattern

def test_element_find_click():
    assert find_by_name('Calculator')

def test_ocr_fallback_click():
    assert click_pattern('OK')
