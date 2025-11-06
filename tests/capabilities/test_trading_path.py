from trading.mt5_spec_runner import probe
from trading.paper_engine import run_paper
from trading.risk_engine import metrics_for_run

def test_backtest_metrics():
    assert run_paper()['bars']==200

def test_risk_checks():
    assert metrics_for_run('RUN1')['run']=='RUN1'

def test_no_live_trade():
    assert probe()
