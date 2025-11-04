# ASCII-only LIKE/FTS escape helpers
from __future__ import annotations

def escape_like_literal(term: str, escape_char: str = '\\') -> str:
    if term is None:
        return ''
    s = str(term)
    s = s.replace(escape_char, escape_char + escape_char)
    s = s.replace('%', escape_char + '%')
    s = s.replace('_', escape_char + '_')
    return s


def like_pattern(term: str, escape_char: str = '\\') -> tuple[str, str]:
    lit = escape_like_literal(term, escape_char=escape_char)
    return f"%{lit}%", escape_char


def quote_fts(term: str) -> str:
    s = str(term)
    # Basic double-quote wrapping, escape inner quotes
    return '"' + s.replace('"', '""') + '"'
