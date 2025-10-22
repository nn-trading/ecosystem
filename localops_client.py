from __future__ import annotations

import os
import json
import asyncio


class LocalOpsClient:
    """
    Async client for localops_api.
    Uses httpx if available, otherwise falls back to stdlib urllib in a thread.
    """

    def __init__(self):
        self.base = os.environ.get("LOCALOPS_URL", "http://127.0.0.1:8421").rstrip("/")
        token = os.environ.get("LOCALOPS_TOKEN") or ""
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._mode = "stdlib"
        self._client = None

        try:
            import httpx  # noqa: F401
            self._mode = "httpx"
        except Exception:
            self._mode = "stdlib"

        if self._mode == "httpx":
            import httpx
            self._client = httpx.AsyncClient(
                base_url=self.base,
                headers=self.headers,
                timeout=30,
            )

    async def close(self):
        if self._mode == "httpx" and self._client is not None:
            await self._client.aclose()

    # --- helpers

    async def _get(self, path: str):
        if self._mode == "httpx":
            r = await self._client.get(path)
            r.raise_for_status()
            return r.json()
        else:
            import urllib.request
            import ssl

            def _do():
                req = urllib.request.Request(self.base + path, headers=self.headers, method="GET")
                ctx = ssl.create_default_context()
                with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                    return json.loads(resp.read().decode("utf-8"))

            return await asyncio.to_thread(_do)

    async def _post(self, path: str, payload: dict):
        if self._mode == "httpx":
            r = await self._client.post(path, json=payload)
            r.raise_for_status()
            return r.json()
        else:
            import urllib.request
            import ssl

            def _do():
                data = json.dumps(payload or {}).encode("utf-8")
                headers = dict(self.headers)
                headers["Content-Type"] = "application/json"
                req = urllib.request.Request(self.base + path, data=data, headers=headers, method="POST")
                ctx = ssl.create_default_context()
                with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                    return json.loads(resp.read().decode("utf-8"))

            return await asyncio.to_thread(_do)

    # --- API

    async def health(self):
        return await self._get("/health")

    async def fs_write(self, relpath: str, text: str):
        return await self._post("/fs/write", {"relpath": relpath, "text": text})

    async def fs_read(self, relpath: str):
        return await self._post("/fs/read", {"relpath": relpath})

    async def fs_ls(self, relpath: str):
        return await self._post("/fs/ls", {"relpath": relpath})

    async def run(self, cmd: str, cwd: str | None = None, timeout: int = 30):
        payload = {"cmd": cmd}
        if cwd:
            payload["cwd"] = cwd
        if timeout:
            payload["timeout"] = timeout
        return await self._post("/shell/run", payload)
