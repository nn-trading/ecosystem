# scripts/maint_sweep.ps1  stop ecosys jobs, vacuum events.db, run smoke, show probe tails
# Usage: powershell -NoProfile -File scripts\maint_sweep.ps1

# Stop PS jobs and any ecosys-bound Python
Get-Job | Stop-Job -ErrorAction SilentlyContinue; Get-Job | Remove-Job -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process | Where-Object {
  $_.Name -match "python" -and $_.CommandLine -match "C:\\bots\\ecosys"
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

# Vacuum var/events.db (robust, offline)
$py = Join-Path $PWD ".venv\Scripts\python.exe"; if (!(Test-Path $py)) { $py = "python" }
$code = @"
import sqlite3, sys, time
p = r"C:\bots\ecosys\var\events.db"
for i in range(10):
    try:
        conn = sqlite3.connect(p, timeout=1, isolation_level=None)
        cur = conn.cursor()
        cur.execute("PRAGMA busy_timeout=1000")
        cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        cur.execute("VACUUM")
        conn.close()
        print("EVENTS_DB_VACUUM_OK")
        break
    except Exception as e:
        print("RETRY", i, type(e).__name__, e); time.sleep(0.5)
else:
    raise SystemExit("EVENTS_DB_VACUUM_FAILED")
"@
$tmp = Join-Path $env:TEMP "vac_events.py"; Set-Content $tmp $code -Encoding UTF8
& $py $tmp

# Foreground smoke (headless, no background loop)
powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 0

# Print probe tails robustly
function TailText($p){ if(Test-Path $p){ ((Get-Content $p -Raw) -split "\r?\n") | Where-Object {$_} | Select-Object -Last 1 } }
"openai_probe:  $(TailText '.\reports\llm\openai_probe.txt')"
"openrouter_probe:  $(TailText '.\reports\llm\openrouter_probe.txt')"
