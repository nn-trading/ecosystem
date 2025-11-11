# C:\bots\ecosys\core\bus.py
from __future__ import annotations
import asyncio
import inspect
from dataclasses import dataclass
from typing import Any, Dict, Optional, AsyncIterator, List, Tuple

from .envelope import Envelope

class EventBus:
    """
    Minimal, reliable async pub/sub with exact-topic and prefix subscriptions.

    API:
      - await publish(topic, payload, *, sender, job_id=None)
      - async for env in subscribe(topic): ...
      - async for env in subscribe_prefix(prefix): ...
    """
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._subs: Dict[str, List[asyncio.Queue[Envelope]]] = {}
        self._prefix_subs: List[Tuple[str, asyncio.Queue[Envelope]]] = []

    async def publish(
        self,
        topic: str,
        payload: Dict[str, Any],
        *,
        sender: str,
        job_id: Optional[str] = None,
    ) -> None:
        """Publish one event to all matching subscribers."""
        env = Envelope(type=topic, payload=payload or {}, src=sender, job_id=job_id)

        # Take a snapshot of destination queues under lock
        async with self._lock:
            queues: List[asyncio.Queue[Envelope]] = list(self._subs.get(topic, []))
            for prefix, q in list(self._prefix_subs):
                if topic.startswith(prefix):
                    queues.append(q)

        # Deliver outside the lock
        for q in queues:
            await q.put(env)

    async def subscribe(self, topic: str) -> AsyncIterator[Envelope]:
        """
        Subscribe to an exact topic. Yields Envelope objects.
        Cleanly unregisters on generator exit.
        """
        q: asyncio.Queue[Envelope] = asyncio.Queue(maxsize=1000)
        async with self._lock:
            self._subs.setdefault(topic, []).append(q)
        try:
            while True:
                env = await q.get()
                yield env
        finally:
            async with self._lock:
                lst = self._subs.get(topic, [])
                if q in lst:
                    lst.remove(q)

    async def subscribe_prefix(self, prefix: str) -> AsyncIterator[Envelope]:
        """
        Subscribe to ALL topics that start with `prefix`.
        Yields Envelope objects. Cleanly unregisters on exit.
        """
        q: asyncio.Queue[Envelope] = asyncio.Queue(maxsize=1000)
        async with self._lock:
            self._prefix_subs.append((prefix, q))
        try:
            while True:
                env = await q.get()
                yield env
        finally:
            async with self._lock:
                self._prefix_subs = [(p, qq) for (p, qq) in self._prefix_subs if qq is not q]

    # --- Compatibility adapters ---
    def on(self, topic: str, handler):
        """
        Back-compat adapter: register a coroutine/callable handler for a topic.
        Spawns a background task to consume subscribe(topic) and invoke handler.
        Returns None (non-awaitable).
        """
        loop = asyncio.get_event_loop()
        async def _runner():
            async for env in self.subscribe(topic):
                try:
                    if inspect.iscoroutinefunction(handler):
                        await handler({"topic": env.topic, "data": env.payload, "job_id": env.job_id})
                    else:
                        res = handler({"topic": env.topic, "data": env.payload, "job_id": env.job_id})
                        if inspect.isawaitable(res):
                            await res
                except Exception:
                    # never crash the runner
                    pass
        loop.create_task(_runner(), name=f"bus.on[{topic}]")
        return None

    async def emit(self, topic: str, payload: Dict[str, Any], *, sender: str, job_id: Optional[str] = None):
        return await self.publish(topic, payload, sender=sender, job_id=job_id)

    async def send(self, topic: str, payload: Dict[str, Any], *, sender: str, job_id: Optional[str] = None):
        return await self.publish(topic, payload, sender=sender, job_id=job_id)

# Back-compat for older modules that import MessageBus
MessageBus = EventBus
