from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Any, Dict

@dataclass
class UserRequest:
    text: str

@dataclass
class PlanReady:
    plan: str

@dataclass
class WorkRequest:
    action: str
    args: Dict[str, Any]

@dataclass
class WorkResult:
    ok: bool
    detail: str = ""
    artifact_path: Optional[str] = None

@dataclass
class TestPassed:
    name: str

@dataclass
class TestFailed:
    name: str
    fix_brief: str

@dataclass
class Done:
    msg: str = "done"

@dataclass
class LogEvent:
    level: str
    msg: str
    extra: Dict[str, Any] | None = None
