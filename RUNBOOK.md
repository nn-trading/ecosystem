# Runbook

This file tracks session status and resume checkpoints. ASCII-only/UTF-8.

## Current status
- Repo: C:\bots\ecosys
- Branch: eval-battery-and-maintenance-fixes
- Commit: a6f4f9d
- Tools: winui_pid LRESULT fallback in place; import OK (Python 3.12). SendMessageW.restype=c_longlong.
- Tests: pytest 19 passed, 1 skipped (UI macro; gated by AGENT_DANGER_MODE), 2 warnings
- Pip: restored via ensurepip; requirements installed
- Working tree: clean after commit

## Latest checks (2025-10-28)
- ToolsRegistry: lists win.* and ui.* tools; registry OK
- winui_pid: Python 3.12.10 import OK; SendMessageW.restype is ctypes.c_longlong; no import errors
- Runtime tasks: logs/tasks.json shows T1..T8 all done
- Encoding: continue ASCII-only in tracked files

## Task tracking snapshot
- RST-08: done (Recovery/Status handoff; RUNBOOK updated)
- CHK-01: done (Git clean; latest commit a6f4f9d)
- CHK-02: done (Runtime registry check; winui_pid LRESULT verified)
- UI-01: done (paste equality verification + recursion bug removed)
- UI-02: done (Notepad equality macro test added; skip unless AGENT_DANGER_MODE=1)
- NET-01: done (weather.get fallback mirrors + normalized fields)
- NET-02: done (fx.convert fallback to frankfurter.app; normalized fields)
- NET-03: done (http.fetch retries/backoff exists)
- CORE-01: todo (Brain intent detection + fuzzy replanning)
- CORE-02: todo (Tester assertions + loop fix)
- CORE-03: todo (Logger/Memory SQLite + runs/<ts>/ artifacts + summarizer)
- ASCII-01: todo (ASCII-safe writer + sanitize writes)
- ASAT-01: todo (Run mini acceptance suite and collect artifacts)
- TEST-01: done (Pytest installed; passing)
- REP-01: todo (Produce ASAT final audit and output path + commit hash)

## Next steps
- Implement CORE-01/02/03, ASCII-01, ASAT-01, REP-01
- Keep artifacts ASCII-safe; continue to gate UI tests by AGENT_DANGER_MODE

## Notes
- TASKS.md is ignored by .gitignore; this runbook is tracked for status persistence.
- Keep logs/session_status.txt as ASCII-only; it's ignored by git.
