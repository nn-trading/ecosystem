SEARCH AND DB NOTES

Unified DB path precedence
- ECOSYS_LOGGER_DB > ECOSYS_MEMORY_DB > var\events.db
- Default path: C:\bots\ecosys\var\events.db

Search strategy
- FTS5 first: queries run against events_fts when available
- Safe fallback: if FTS fails or returns empty for special tokens, fall back to LIKE with ESCAPE '\'
- LIKE rules: payload_json and topic/type columns searched with patterns built via escaping %, _ and \
- Quoting: if FTS throws on quotes, retry with the term wrapped in double quotes with inner quotes doubled

Field mapping
- EventLog columns: topic, sender, payload_json
- LoggerDB columns: type, agent, payload_json (mapped to EventLog topic/sender when available)
- Practical guidance: prefer payload text searches; use topic: or topic= prefix for EventLog topic matches

Examples
- Stats:    python dev\loggerdb_cli.py stats
- Search:   python dev\loggerdb_cli.py search "backslash\path"
- Search:   python dev\loggerdb_cli.py search "topic:heartbeat"
- Snapshot: python dev\loggerdb_cli.py snapshot-run -n 200

Notes
- Both EventLog and LoggerDB share var\events.db by default
- Set ECOSYS_LOGGER_DB or ECOSYS_MEMORY_DB to override the database path at runtime
