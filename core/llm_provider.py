import os, json
from typing import Optional

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

try:
    import httpx
except Exception:
    httpx = None

# Absolute config path so dev/probe works regardless of CWD
CFG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "llm.yaml")

def _load_cfg() -> dict:
    prov, model = "openai", "gpt-5"
    try:
        import yaml  # type: ignore
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            d = (yaml.safe_load(f) or {})
            prov = (d.get("provider") or prov).strip()
            model = (d.get("model") or model).strip()
    except Exception:
        pass
    return {"provider": prov, "model": model}

# ---------- Providers ----------
class OpenAIProvider:
    def __init__(self, model: Optional[str] = None):
        self.model = model or "gpt-5"
        self.api_key = os.environ.get("OPENAI_API_KEY")
        # Optional base URL support
        base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE")
        if OpenAI:
            try:
                kwargs = {"api_key": self.api_key}
                if base_url:
                    kwargs["base_url"] = base_url
                self.client = OpenAI(**kwargs)
            except Exception:
                self.client = None
        else:
            self.client = None

    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        if not self.client:
            return "[openai error: SDK not available]"
        m = (self.model or "").lower()
        try:
            if m.startswith("gpt-5"):
                # Responses API for GPT-5 family
                # If a system prompt is provided, pass as structured input
                if system:
                    input_payload = [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ]
                else:
                    input_payload = prompt
                resp = self.client.responses.create(model=self.model, input=input_payload)
                text = getattr(resp, "output_text", None)
                if text:
                    return text.strip()
                try:
                    return json.dumps(resp.model_dump())
                except Exception:
                    return str(resp)
            else:
                # Chat for other OpenAI models (no temperature for maximum compat)
                msgs = []
                if system:
                    msgs.append({"role": "system", "content": system})
                msgs.append({"role": "user", "content": prompt})
                resp = self.client.chat.completions.create(model=self.model, messages=msgs)
                return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            return f"[openai error: {e}]"

class OpenRouterProvider:
    def __init__(self, model: Optional[str] = None):
        self.model = model or "openai/gpt-4o-mini"
        self.key = os.environ.get("OPENROUTER_API_KEY")
        self.referer = os.environ.get("OPENROUTER_HTTP_REFERER") or "https://github.com/nn-trading/ecosystem"
        self.xtitle  = os.environ.get("OPENROUTER_X_TITLE") or "ecosys"
        # Allow OPENAI_BASE_URL override for proxy compatibility; default to OpenRouter
        self.base = os.environ.get("OPENAI_BASE_URL") or "https://openrouter.ai/api/v1"

    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        if not httpx:
            return "[openrouter error: httpx not installed]"
        try:
            hdr = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.key}" if self.key else "",
                "HTTP-Referer": self.referer,
                "Referer": self.referer,
                "X-Title": self.xtitle,
            }
            msgs = []
            if system:
                msgs.append({"role": "system", "content": system})
            msgs.append({"role": "user", "content": prompt})
            body = {"model": self.model, "messages": msgs}
            r = httpx.post(f"{self.base}/chat/completions", headers=hdr, json=body, timeout=60)
            r.raise_for_status()
            j = r.json()
            return (j.get("choices", [{}])[0].get("message", {}).get("content", "") or "").strip()
        except Exception as e:
            return f"[openrouter error: {e}]"

class LocalGptOssProvider:
    def __init__(self, model: Optional[str] = None):
        self.model = model or "llama3.1:8b-instruct"
        self.base = os.environ.get("OLLAMA_BASE_URL") or "http://127.0.0.1:11434"

    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        if not httpx:
            return "[gpt-oss error: httpx not installed]"
        try:
            msgs = []
            if system:
                msgs.append({"role": "system", "content": system})
            msgs.append({"role": "user", "content": prompt})
            body = {"model": self.model, "messages": msgs}
            r = httpx.post(f"{self.base}/api/chat", json=body, timeout=60)
            r.raise_for_status()
            j = r.json()
            # result schema can be streaming or single; handle common case:
            if isinstance(j, dict):
                msg = (j.get("message") or {}).get("content")
                if msg:
                    return msg.strip()
            return str(j)[:500]
        except Exception as e:
            return f"[gpt-oss error: {e}]"

# Back-compat factory used elsewhere

def load_provider(provider: str, model: str):
    p = (provider or "openai").strip().lower()
    if p == "openrouter":
        return OpenRouterProvider(model)
    if p in ("gpt-oss", "ollama", "local"):
        return LocalGptOssProvider(model)
    return OpenAIProvider(model)


def provider_factory():
    cfg = _load_cfg()
    return load_provider(cfg.get("provider", "openai"), cfg.get("model", "gpt-5"))
