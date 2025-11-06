OPERATIONS QUICKSTART (Windows, PowerShell)

Stop background
- powershell -NoProfile -File .\start.ps1 -Stop 1

Start headless
- powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 1 -EnsureVenv 1 -EnsureDeps 0 -RunPytest 0 -HeartbeatSec 2 -HealthSec 2

Health check
- .\.venv\Scripts\python.exe dev\obs_cli.py recent -n 20

Snapshots and maintenance
- python dev\loggerdb_cli.py snapshot-run -n 200
- python dev\health_check.py
- python dev\eventlog_cli.py stats

Where proofs live
- reports\capability_matrix.json
- runs\<snapshot>
- logs and reports for health and summaries
