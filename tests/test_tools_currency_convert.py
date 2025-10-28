# Test currency.convert with stubbed urllib
import os, sys
import json
import types

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools import currency


class FakeResponse:
    def __init__(self, text):
        self._text = text.encode("utf-8")
    def read(self):
        return self._text


def test_currency_convert_success(monkeypatch):
    def fake_urlopen(req, timeout=None, context=None):
        # Validate URL shape
        url = getattr(req, 'full_url', getattr(req, 'selector', ''))
        assert "from=USD" in url and "to=EUR" in url and "amount=10" in url
        body = json.dumps({"result": 9.1, "info": {"rate": 0.91}})
        return FakeResponse(body)
    monkeypatch.setattr(currency.urllib.request, "urlopen", fake_urlopen)
    res = currency.convert(10, "usd", "eur")
    assert res.get("ok") is True
    assert res.get("from") == "USD" and res.get("to") == "EUR"
    assert res.get("rate") == 0.91
    assert res.get("result") == 9.1


def test_currency_convert_bad_json(monkeypatch):
    def fake_urlopen(req, timeout=None, context=None):
        return FakeResponse("not-json")
    monkeypatch.setattr(currency.urllib.request, "urlopen", fake_urlopen)
    res = currency.convert(5, "usd", "eur")
    assert res.get("ok") is False
