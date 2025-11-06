ASCII ONLY POLICY

Scope
- All persisted artifacts must be ASCII-only
- Allowed write targets include: logs, reports, var, runs, docs, dev

Known pitfalls
- Emoji and non-ASCII characters in Markdown or JSON cause encoding failures on Windows
- Avoid writing sessions/TASKS.md (uses emoji); use logs/tasks.json and reports/TASKS_ASCII.md instead

Canonical trackers
- logs/tasks.json is canonical for tasks
- reports/TASKS_ASCII.md is the human-readable view
