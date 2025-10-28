# Runbook

This file tracks session status and resume checkpoints. ASCII-only/UTF-8.

## Current status
- Repo: C:\bots\ecosys
- Branch: eval-battery-and-maintenance-fixes
- Headless: running; health OK; auto-resume shown in logs
- Tools: winui_pid LRESULT fallback in place; import OK (Python 3.12)
- Tests: pytest 17 passed, 2 warnings
- Untracked: none (tmp files removed)

## Session plan
- T01: Discover saved logs/notes/checkpoints — done
- T02: Execute maintenance pipeline — done
- T03: Verify environment status and auto-resume — done
- T04: Report consolidated status and next steps — done
- T05: Fix tools.winui_pid import error if present — done
- T06: VACUUM events.db safely — done
- T07: Version control hygiene — done
- T08: Persist consolidated status to RUNBOOK — done
- T09: Re-verify headless logs for winui_pid import errors — done

## Notes
- TASKS.md is ignored by .gitignore; this runbook is tracked for status persistence.
- Keep logs/session_status.txt as ASCII-only; it's ignored by git.
