from memory.db_tuning import apply_db_pragmas

def test_db_wal_and_busy_timeout(tmp_path):
    db = tmp_path/'t.db'
    stat = apply_db_pragmas(str(db))
    assert stat['wal'] and stat['busy_timeout']==3000

def test_cost_cap_enforced_soft():
    from costs.cost_governor import status, set_daily_cap
    set_daily_cap(3.0)
    assert status()['daily_cap']==3.0
