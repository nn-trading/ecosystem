# C:\bots\ecosys\core\llm_client.py
from __future__ import annotations
import os, asyncio
from typing import Tuple, Optional

class LLMClient:
    """
    Thin wrapper with:
      - timeout_sec support
      - OpenAI v1 (openai.OpenAI) or legacy v0 (openai.ChatCompletion) support
      - base_url override via OPENAI_BASE_URL / OPENAI_API_BASE
      - graceful offline fallback for router/chat/brain plans
    Usage:
      ok, msg = await complete(system="...", user="...")
    Returns:
      (True, string) on success; (False, error_string) on failure
    """
    def __init__(self, timeout_sec: int = 45):
        self.timeout = int(timeout_sec)
        self.model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE") or None

        self._client = None
        self._mode = "none"
        # Try OpenAI v1 first
        try:
            if self.api_key:
                try:
                    from openai import OpenAI  # v1+
                    kwargs = {}
                    if self.base_url:
                        kwargs["base_url"] = self.base_url
                    self._client = OpenAI(api_key=self.api_key, **kwargs)
                    self._mode = "openai_v1"
                except Exception:
                    # Try legacy v0
                    import openai  # type: ignore
                    openai.api_key = self.api_key
                    if self.base_url:
                        openai.api_base = self.base_url
                    self._client = openai
                    self._mode = "openai_v0"
        except Exception:
            self._client = None
            self._mode = "none"

    async def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> Tuple[bool, Optional[str]]:
        """Async wrapper with timeout."""
        try:
            return await asyncio.wait_for(
                self._complete_sync(system, user, max_tokens, temperature),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            return False, "timeout"
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"

    async def _complete_sync(self, system, user, max_tokens, temperature):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, lambda: self._complete_blocking(system, user, max_tokens, temperature)
        )

    def _complete_blocking(self, system, user, max_tokens, temperature):
        # --- OpenAI v1 ---
        if self._mode == "openai_v1":
            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                content = resp.choices[0].message.content if resp and resp.choices else ""
                if content is None:
                    content = ""
                return True, content
            except Exception as e:
                return False, f"OpenAI(v1) error: {e}"

        # --- OpenAI v0 (legacy) ---
        if self._mode == "openai_v0":
            try:
                resp = self._client.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                content = resp["choices"][0]["message"]["content"] if resp and resp.get("choices") else ""
                return True, content
            except Exception as e:
                return False, f"OpenAI(v0) error: {e}"

        # --- Offline fallback (no API) ---
        # Router prompt detection -> decide CHAT or TASK
        if "CHAT or TASK" in (system or ""):
            text = (user or "").strip().lower()
            actiony = [
                "zip","unzip","create","write","read","append","copy","move","delete",
                "run","shell","powershell","search","grep","screenshot","install","pip",
                "weather","http","web","fetch","download","open url","browse","calculate","translate"
            ]
            if any(k in text for k in actiony) or text.endswith("?"):
                # Questions default to TASK in offline mode so we actually try to do something.
                return True, "TASK"
            return True, "CHAT"

        # Chat system
        if "communication AI" in (system or ""):
            # Keep it short in offline mode
            return True, "Sure—what should I do?"

        # Brain planning system (expects JSON)
        if "Return ONLY JSON with keys: title" in (system or ""):
            # Minimal fallback plan
            minimal = {
                "title": "Action Plan",
                "rationale": "Offline fallback",
                "steps": [
                    {"type": "reason", "description": "Fallback: inspect workspace"},
                    {"type": "tool", "tool": "fs.ls", "args": {"path": r"C:\bots\ecosys"}, "description": "List workspace"},
                ],
            }
            import json as _json
            return True, _json.dumps(minimal)

        # Default generic
        return True, "OK"
