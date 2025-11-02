from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple

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

# ---- Planner API and evaluator (CORE-01) ----
from typing import Tuple

def planner_make_plan_from_intent(intent: Intent) -> Dict[str, Any]:
    title = f"Plan for: {intent.goal}" if intent.goal else "Plan"
    steps: List[Dict[str, Any]] = []
    if intent.goal:
        steps.append({"type": "reason", "description": f"Goal: {intent.goal}"})
    for c in intent.constraints:
        steps.append({"type": "reason", "description": f"Constraint: {c}"})
    if intent.success:
        steps.append({"type": "reason", "description": "Success when: " + "; ".join(intent.success)})
    # Baseline execution step
    steps.extend(plan_steps(intent))
    return {"title": title, "rationale": "Parsed intent and built baseline plan", "steps": steps}

def planner_make_plan(text: str) -> Dict[str, Any]:
    return planner_make_plan_from_intent(parse_intent(text or ""))

def evaluate_success_from_texts(success: List[str], texts: List[str]) -> Dict[str, Any]:
    succ = [str(s).strip().lower() for s in (success or []) if str(s).strip()]
    matched: List[str] = []
    hay = [str(t).lower() for t in (texts or [])]
    if succ:
        for s in succ:
            for t in hay:
                if s in t:
                    matched.append(s)
                    break
    else:
        for t in hay:
            if ("success" in t) or ("done" in t) or ("completed" in t):
                matched.append("implicit")
                break
    ok = (len(matched) >= min(1, len(succ))) if succ else bool(matched)
    return {"ok": bool(ok), "matched": matched}

def replan_if_needed(plan: Dict[str, Any], evaluation: Dict[str, Any]) -> Dict[str, Any]:
    if evaluation.get("ok"):
        return plan
    steps = list(plan.get("steps") or [])
    steps.append({"type": "reason", "description": "Replan: prior attempt did not meet success; adjust or request clarification"})
    plan2 = dict(plan)
    plan2["steps"] = steps
    plan2["rationale"] = (plan.get("rationale") or "").rstrip() + " | Replan added"
    return plan2

