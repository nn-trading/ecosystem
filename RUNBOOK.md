# Runbook

This file tracks session status and resume checkpoints. ASCII-only/UTF-8.

## Current status
- Repo: C:\bots\ecosys
- Branch: eval-battery-and-maintenance-fixes
- Commit: 93b111a
- Tools: winui_pid LRESULT fallback in place; import OK (Python 3.12). SendMessageW.restype=c_longlong.
- Tests: pytest 17 passed, 1 skipped (UI macro; gated by AGENT_DANGER_MODE), 2 warnings
- Pip: restored via ensurepip; requirements installed
- Working tree: clean

## Latest checks (2025-10-28)
- ToolsRegistry: lists win.* and ui.* tools; registry OK
- winui_pid: Python 3.12.10 import OK; SendMessageW.restype is ctypes.c_longlong; no import errors
- Runtime tasks: logs/tasks.json shows T1..T8 all done
- Encoding: continue ASCII-only in tracked files

## Task tracking snapshot
- RST-08: in_progress (Recovery/Status: summarize and hand off)
- CHK-01: done (Git clean; latest commit 7c7bfef -> superseded by 93b111a)
- CHK-02: done (Runtime registry check; winui_pid LRESULT verified)
- UI-01: done (paste equality verification + recursion bug removed)
- UI-02: todo (Notepad macro equality test added; skipped by default unless danger mode)
- NET-01: todo (weather.get fallback and normalized output)
- NET-02: todo (fx.convert fallback and normalized output)
- NET-03: done (http.fetch retries/backoff exists)
- CORE-01: todo (Brain intent detection + fuzzy replanning)
- CORE-02: todo (Tester assertions + loop fix)
- CORE-03: todo (Logger/Memory SQLite + runs/<ts>/ artifacts + summarizer)
- ASCII-01: todo (ASCII-safe writer + sanitize writes)
- ASAT-01: todo (Run mini acceptance suite and collect artifacts)
- TEST-01: done (Pytest installed; 17 passed)
- REP-01: todo (Produce ASAT final audit and output path + commit hash)

## Next steps
- Implement NET-01/NET-02 provider fallbacks and normalized schemas
- Implement CORE-01/02/03, ASCII-01, ASAT-01, REP-01
- Keep artifacts ASCII-safe; continue to gate UI tests by AGENT_DANGER_MODE

## Notes
- TASKS.md is ignored by .gitignore; this runbook is tracked for status persistence.
- Keep logs/session_status.txt as ASCII-only; it's ignored by git.
