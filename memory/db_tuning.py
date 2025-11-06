import sqlite3

def apply_db_pragmas(path: str):
    con = sqlite3.connect(path)
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA busy_timeout=3000')
    con.close()
    return {'wal': True, 'busy_timeout': 3000}
