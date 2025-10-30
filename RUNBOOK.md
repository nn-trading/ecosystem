# Runbook

This file tracks session status and resume checkpoints. ASCII-only/UTF-8.

## Current status
- Repo: C:\bots\ecosys
- Branch: eval-battery-and-maintenance-fixes
- Commit: d978a82
- Tools: winui_pid LRESULT fallback in place; import OK (Python 3.12). SendMessageW.restype=c_longlong.
- Tests: pytest 30 passed, 1 skipped (UI macro; gated by AGENT_DANGER_MODE), 3 warnings
- Pip: restored via ensurepip; requirements installed
- Working tree: clean

## Latest checks (2025-10-30)
- ToolsRegistry: lists win.* and ui.* tools; registry OK
- winui_pid: Python 3.12.10 import OK; SendMessageW.restype is ctypes.c_longlong; no import errors
- Eval battery: 154 tasks enumerated; clean run produced 148 pass, 6 fail previously; current ASAT below
- Encoding: continue ASCII-only in tracked files

## Task tracking snapshot
- RST-08: done
- RST-09: done
- RST-10: done (Loaded logs, confirmed repo state; HEAD 6515b76; tests last known 21 passed, 1 skipped)
- CHK-01: done
- CHK-02: done
- UI-01: done
- UI-02: done
- NET-01: done
- NET-02: done
- NET-03: done
- CORE-01: todo (Brain intent detection + fuzzy replanning + success criteria)
- CORE-02: todo (Tester assertions + loop fix)
- CORE-03: todo (Logger/Memory SQLite + runs/<ts>/ artifacts + summarizer)
- ASCII-01: in_progress (ASCII-safe writer + unit test implemented; adoption across writers pending)
- ASAT-01: done (asat_runner implemented; writes ASCII artifacts)
- ASAT-02: done (ASAT run completed; artifacts recorded)
- TEST-01: done
- TEST-ALL: done (suite green)
- DOC-01: done
- DOC-02: done (RUNBOOK updated: commit/test counts and task statuses)
- REP-01: done (ASAT final audit recorded with output path + commit hash)

## Next steps
- Implement CORE-01/02/03, ASCII-01, ASAT-01, REP-01
- Keep artifacts ASCII-safe; continue to gate UI tests by AGENT_DANGER_MODE


## ASAT (Acceptance Suite Audit)
- Last run: 2025-10-28 20:34:46 UTC
- Output directory: C:\bots\ecosys\runs\20251028_203446
- Commit: 27382c20e77684e02a33553a63f629669d0a0003
- Artifacts:
  - report: C:\bots\ecosys\runs\20251028_203446\report.txt
  - results: C:\bots\ecosys\runs\20251028_203446\results.jsonl
  - summary: C:\bots\ecosys\runs\20251028_203446\summary.json
- Notes: Artifacts are ASCII-only. Eval battery used tools/eval_runner; 154 tasks enumerated.

## Notes
- TASKS.md is ignored by .gitignore; this runbook is tracked for status persistence.
- Keep logs/session_status.txt as ASCII-only; it's ignored by git.

