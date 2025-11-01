from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any

ASCII_JSON_KW = dict(ensure_ascii=True, separators=(",", ":"))

@dataclass
class Intent:
    goal: str = ""
    constraints: List[str] = field(default_factory=list)
    success: List[str] = field(default_factory=list)


def parse_intent(text: str) -> Intent:
    if not text:
        return Intent()
    t = text.strip()
    # Very simple heuristics: look for goal, constraints, success keywords
    goal = t
    m = re.search(r"goal[:\-]\s*(.+)", t, re.I)
    if m:
        goal = m.group(1).strip()
    cons = re.findall(r"(?:constraint|must)[:\-]\s*([^\n;]+)", t, re.I)
    succ = re.findall(r"(?:success|done|accept)[:\-]\s*([^\n;]+)", t, re.I)
    # Also parse bracketed [success: ...] or (success: ...)
    succ += re.findall(r"[\[(]success[:\-]\s*([^\]\)]+)[\]\)]", t, re.I)
    # Normalize
    constraints = [c.strip() for c in cons if c.strip()]
    success = [s.strip() for s in succ if s.strip()]
    return Intent(goal=goal, constraints=constraints, success=success)


def plan_steps(intent: Intent) -> List[Dict[str, Any]]:
    steps: List[Dict[str, Any]] = []
    if not intent or not intent.goal:
        return steps
    # Baseline: one step that echoes goal; constraints and success recorded
    steps.append({
        "action": "plan",
        "description": intent.goal,
        "constraints": list(intent.constraints),
        "success": list(intent.success),
    })
    return steps
