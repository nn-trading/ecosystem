# C:\bots\ecosys\core\summarizer.py
from __future__ import annotations
import asyncio
from collections import Counter
from typing import Any, Iterable, List, Sequence, Union, Tuple

MAX_CHARS_DEFAULT = 4000

def _coerce_lines(lines_or_text: Union[str, Sequence[str]]) -> List[str]:
    """Accept str or list[str]; always return list[str] (non-empty, trimmed)."""
    if lines_or_text is None:
        return []
    if isinstance(lines_or_text, str):
        # splitlines keeps meaningful breaks without producing single characters
        return [ln.strip() for ln in lines_or_text.splitlines() if ln.strip()]
    # assume it's an iterable of lines
    out: List[str] = []
    for x in lines_or_text:
        if x is None:
            continue
        s = str(x).strip()
        if s:
            out.append(s)
    return out

def _parse_line(line: str) -> Tuple[str, str, str]:
    """
    Expect the logger's compact format:
        "<sender> :: <topic> :: <frag>"
    If not matching, return ("", "", line).
    """
    parts = [p.strip() for p in line.split("::", 2)]
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    return "", "", line.strip()

async def _maybe_llm_summary(llm: Any, text: str) -> str:
    """
    Try a few common client methods; fall back gracefully if anything fails.
    This is defensive and won't crash the caller.
    """
    if llm is None:
        return ""
    try:
        if hasattr(llm, "acomplete") and callable(llm.acomplete):
            # async completion(text) -> str
            return str(await llm.acomplete(text))[:MAX_CHARS_DEFAULT]
    except Exception:
        pass
    try:
        if hasattr(llm, "complete") and callable(llm.complete):
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(None, lambda: llm.complete(text))
            return str(res)[:MAX_CHARS_DEFAULT]
    except Exception:
        pass
    try:
        if hasattr(llm, "chat") and callable(llm.chat):
            # Some clients expose a chat() that takes a prompt
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(None, lambda: llm.chat(text))
            return str(res)[:MAX_CHARS_DEFAULT]
    except Exception:
        pass
    return ""

def _heuristic_summary(lines: List[str], max_chars: int) -> str:
    """
    LLM-free robust summary:
      - counts by sender/topic
      - last user inputs
      - last tool invocations / PASS|FAIL signals (if present in text fragments)
    """
    senders = Counter()
    topics  = Counter()
    user_last: List[str] = []
    tool_calls: List[str] = []
    results: List[str] = []

    for ln in lines:
        sender, topic, frag = _parse_line(ln)
        if sender: senders[sender] += 1
        if topic:  topics[topic]  += 1

        # track last few user messages
        if topic.lower() == "user/text" and frag:
            user_last.append(frag)

        # crude signals for tool/run lines and PASS/FAIL from tester/worker logs
        f = frag.lower()
        if any(key in f for key in ("fs.", "zip.", "scr.", "shell.run", "ps.run", "weather.current", "web.http_get", "web.get_json", "find.grep")):
            tool_calls.append(frag[:200])
        if "[tester]" in ln.lower() or "pass" in f or "fail" in f:
            if "pass" in f:
                results.append("PASS")
            elif "fail" in f:
                results.append("FAIL")

    # pick last few items for display
    user_show   = user_last[-5:]
    tools_show  = tool_calls[-8:]
    pass_count  = results.count("PASS")
    fail_count  = results.count("FAIL")

    top_senders = ", ".join(f"{k}×{v}" for k,v in senders.most_common(5))
    top_topics  = ", ".join(f"{k}×{v}" for k,v in topics.most_common(8))

    parts: List[str] = []
    parts.append("## Session Summary (rolling)")
    parts.append("")
    parts.append(f"- Lines summarized: {len(lines)}")
    if top_senders:
        parts.append(f"- Most active agents: {top_senders}")
    if top_topics:
        parts.append(f"- Frequent topics: {top_topics}")
    if pass_count or fail_count:
        parts.append(f"- Test outcomes (recent): PASS={pass_count} FAIL={fail_count}")
    if user_show:
        parts.append("")
        parts.append("### Recent user messages")
        for u in user_show:
            parts.append(f"- {u}")
    if tools_show:
        parts.append("")
        parts.append("### Recent tool calls")
        for t in tools_show:
            parts.append(f"- {t}")

    text = "\n".join(parts).strip()
    return text[:max_chars] if len(text) > max_chars else text

async def summarize_chat(llm: Any, lines_or_text: Union[str, Sequence[str]], max_chars: int = MAX_CHARS_DEFAULT) -> str:
    """
    Public API used by LoggerAgent.
    Accepts str or list[str]; never returns the silly per-character bullets again.
    """
    lines = _coerce_lines(lines_or_text)
    if not lines:
        return "## Session Summary (rolling)\n\n- (no events)"

    # Try LLM for a paragraph summary of the **lines joined**, not characters.
    prompt = (
        "Summarize the following event lines into a compact status for an autonomous multi-agent system. "
        "Prefer recent user intents, major tool actions, and PASS/FAIL outcomes. Keep it under 600 words.\n\n"
        + "\n".join(lines)
    )
    llm_text = await _maybe_llm_summary(llm, prompt)
    if llm_text:
        # Truncate and return
        llm_text = llm_text.strip()
        return llm_text[:max_chars] if len(llm_text) > max_chars else llm_text

    # Fallback heuristic if LLM not available
    return _heuristic_summary(lines, max_chars)
