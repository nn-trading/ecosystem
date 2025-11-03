# Next Steps

Top 5 tasks:
1) Background health check and tail logs
   powershell -NoProfile -Command "Get-Content -LiteralPath .\\logs\\start_stdout.log -Tail 200 -Wait"
2) Foreground 60s smoke to validate active ops
   powershell -NoProfile -File .\\start.ps1 -Headless 1 -Background 0 -StopAfterSec 60 -RunPytest 0
3) Full test run and capture report
   powershell -NoProfile -File .\\start.ps1 -Headless 0 -Background 0 -RunPytest 1
4) EventLog triage for warnings/errors
   .\\.venv\\Scripts\\python.exe dev\\eventlog_cli.py search error -n 200
   Note: CLI search takes positional query; e.g., python dev\\eventlog_cli.py search ui/print
5) Rotate logs and vacuum if logs grow large
   powershell -NoProfile -File .\\maintain.ps1 -Vacuum 1 -PurgeLogs 1

Blockers (if any):
- Missing OPENAI_API_KEY: False
- Missing ANTHROPIC_API_KEY: True
- Missing MISTRAL_API_KEY: True
- AZURE_* presence checked as needed

Foreground smoke (60s):
powershell -NoProfile -File .\start.ps1 -Headless 1 -Background 0 -StopAfterSec 60 -RunPytest 0

Full test run:
powershell -NoProfile -File .\start.ps1 -Headless 0 -Background 0 -RunPytest 1

Session notes (ASCII-only):
- Commits: e501fdb, e382aa2
- Smoke-fg attempted via start.ps1 but blocked by harness. Use runs\current\smoke_60s_direct.txt as substitute; rerun with longer timeout if needed.
- Focus next: CORE-01-Design-Outline; CORE-01-Parser-Impl; CORE-01-Planner-API; CORE-01-Evaluator-Replan; CORE-03-Schema-Finalize; CORE-03-CLI-Converge; CORE-03-Snapshot-Spec; CORE-03-Search-Escapes

20251102-112235 snapshot-run created C:\bots\ecosys\runs\20251102-112235
20251102-134358 snapshot-run created C:\bots\ecosys\runs\20251102-134358
