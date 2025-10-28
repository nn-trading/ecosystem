# Tests for currency.convert fallback provider
import os, sys, json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools import currency


class FakeResponse:
    def __init__(self, text: str):
        self._text = text.encode("utf-8")
    def read(self):
        return self._text


def test_currency_convert_fallback_to_frankfurter(monkeypatch):
    def fake_urlopen(req, timeout=None, context=None):
        url = getattr(req, 'full_url', getattr(req, 'selector', ''))
        if "api.exchangerate.host" in url:
            raise OSError("simulated primary provider outage")
        if "api.frankfurter.app" in url:
            body = json.dumps({"rates": {"EUR": 9.1}})
            return FakeResponse(body)
        raise AssertionError("unexpected URL: " + str(url))

    monkeypatch.setattr(currency.urllib.request, "urlopen", fake_urlopen)
    res = currency.convert(10, "usd", "eur")
    assert res.get("ok") is True
    assert res.get("provider") == "frankfurter.app"
    assert res.get("from") == "USD" and res.get("to") == "EUR"
    assert abs(res.get("rate") - 0.91) < 1e-12
    assert abs(res.get("result") - 9.1) < 1e-12
