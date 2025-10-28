# Runbook

This file tracks session status and resume checkpoints. ASCII-only/UTF-8.

## Current status
- Repo: C:\bots\ecosys
- Branch: eval-battery-and-maintenance-fixes
- Headless: running; health OK; auto-resume shown in logs
- Tools: winui_pid LRESULT fallback in place; import OK (Python 3.12)
- Tests: pytest 17 passed, 2 warnings
- Untracked: none (tmp files removed)

## Latest checks (2025-10-28)
- Headless: running (PID 21216); auto-resume messages present; ToolsRegistry lists win.* tools
- winui_pid: Python 3.12.10 import OK; SendMessageW.restype is ctypes.c_longlong; no new import errors seen; historical single occurrence remains in logs/start_stdout.log
- Runtime tasks: logs/tasks.json shows T1..T8 all done
- Git: working tree clean; branch eval-battery-and-maintenance-fixes
- Encoding: continue ASCII-only in tracked files


## Latest checks (2025-10-28)
- Headless: running (PID 21216); auto-resume messages present; ToolsRegistry lists win.* tools
- winui_pid: Python 3.12.10 import OK; SendMessageW.restype is ctypes.c_longlong; no new import errors seen; historical single occurrence remains in logs/start_stdout.log
- Runtime tasks: logs/tasks.json shows T1..T8 all done
- Git: working tree clean; branch eval-battery-and-maintenance-fixes
- Encoding: continue ASCII-only in tracked files


## Session plan
- T01: Discover saved logs/notes/checkpoints - done
- T02: Execute maintenance pipeline - done
- T03: Verify environment status and auto-resume - done
- T04: Report consolidated status and next steps - done
- T05: Fix tools.winui_pid import error if present - done
- T06: VACUUM events.db safely - done
- T07: Version control hygiene - done
- T08: Persist consolidated status to RUNBOOK - done
- T09: Re-verify headless logs for winui_pid import errors - done

## Notes
- TASKS.md is ignored by .gitignore; this runbook is tracked for status persistence.
- Keep logs/session_status.txt as ASCII-only; it's ignored by git.
