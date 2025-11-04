Crash-recovery notes (ASCII-only)

Summary
- Duplicate main runner detected and terminated; core loops and tools watcher remain singletons
- EventLog healthy; stats totals and continuous heartbeats from tools watcher
- ASCII-only policy enforced for logs and artifacts; prefer logs/tasks.json
- Maintenance limited to DB vacuum; no log purge intended

Details
- Prior duplicate: main runner PID 55436 (system Python312) killed
- Active loops confirmed: intent, planner, inbox, tools watcher (singletons)
- EventLog stats observed previously: total around 86495; FTS enabled; rollups 0
- Heartbeats: topic core/tools_watch observed every ~5 sec via CLI search

CLI usage notes
- search takes positional query tokens only (e.g., topic:core/tools_watch); flags like --topic or limit:5 are not supported
- recent has no count argument; post-process if limiting is needed

Maintenance notes
- Use: powershell -NoProfile -File .\maintain.ps1 -Vacuum 1 -PurgeLogs 0
- Caution: a later maintain/run sequence triggered pre-start maintenance that attempted a purge; keep DoMaintain 0 to avoid purge
- events.db vacuum may fail with "database is locked" if a reader holds the DB; retry after stopping background loops

Next actions
- Update dev/STATUS.md and NEXT_STEPS.md with singleton state and CLI health snapshot (done in this session)
- Commit docs; exclude logs/, runs/, reports/, sessions/
- Keep writing tasks to logs/tasks.json only; do not write sessions/TASKS.md
