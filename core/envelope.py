# C:\bots\ecosys\core\envelope.py
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Envelope:
    """
    Standard event envelope used on the EventBus.

    Primary fields (new schema):
      - id: unique id for this envelope
      - ts: timestamp (seconds since epoch)
      - src: sender/source component name
      - dst: optional destination hint
      - type: topic/type string (e.g., "task/new")
      - payload: event payload (dict)
      - meta: auxiliary metadata map
      - job_id: optional correlation id

    Back-compat properties:
      - topic: alias for type
      - sender: alias for src
    """
    type: str
    payload: Dict[str, Any]
    src: str
    job_id: Optional[str] = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    ts: float = field(default_factory=lambda: time.time())
    dst: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    # ---- Back-compat aliases ----
    @property
    def topic(self) -> str:  # legacy name
        return self.type

    @property
    def sender(self) -> str:  # legacy name
        return self.src

    # Minimal dict-like access used by some legacy code paths
    def get(self, key: str, default: Any = None) -> Any:
        if key == "topic":
            return self.type
        if key == "type":
            return self.type
        if key == "payload":
            return self.payload
        if key == "sender":
            return self.src
        if key == "src":
            return self.src
        if key == "job_id":
            return self.job_id
        if key == "meta":
            return self.meta
        return default
