import os, httpx, yaml
from typing import Optional


def load_cfg():
    path = os.path.join("config", "llm.yaml")
    if not os.path.isfile(path):
        return {"provider": "openai", "model": "gpt-5"}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        data = {}
    return {"provider": data.get("provider", "openai"), "model": data.get("model", "gpt-5")}


class OpenAIProvider:
    def __init__(self, model: str):
        self.model = model

    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        try:
            from openai import OpenAI
            client = OpenAI()
            msgs = []
            if system:
                msgs.append({"role": "system", "content": system})
            msgs.append({"role": "user", "content": prompt})
            # IMPORTANT: no temperature argument (some models only accept default)
            out = client.chat.completions.create(model=self.model, messages=msgs)
            return (out.choices[0].message.content or "").strip()
        except Exception as e:
            return f"openai error: {e}"


class OpenRouterProvider:
    BASE = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, model: str):
        self.model = model

    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        key = os.environ.get("OPENROUTER_API_KEY", "")
        if not key:
            try:
                with open(os.path.join("secrets","openrouter.key"), "r", encoding="utf-8") as f:
                    key = f.read().strip()
            except Exception:
                pass
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            # Helpful (not required) metadata:
            "HTTP-Referer": os.environ.get("OPENROUTER_HTTP_REFERER","https://github.com/nn-trading/ecosystem"),
            "Referer": os.environ.get("OPENROUTER_HTTP_REFERER","https://github.com/nn-trading/ecosystem"),
            "X-Title": os.environ.get("OPENROUTER_X_TITLE","ecosystem-ai"),
        }
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        try:
            with httpx.Client(timeout=30.0) as cx:
                r = cx.post(self.BASE, headers=headers, json={"model": self.model, "messages": msgs})
                if r.status_code != 200:
                    return f"openrouter error: {r.status_code} {r.text[:300]}"
                data = r.json()
                return (data["choices"][0]["message"]["content"] or "").strip()
        except Exception as e:
            return f"openrouter error: {e}"


class LocalGptOssProvider:
    def __init__(self, model: str):
        self.model = model

    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        # Stubbed for now (real HF load later)
        return "gpt-oss stub: " + (prompt[:200] if prompt else "")


def load_provider(provider: str, model: str):
    p = (provider or "openai").lower()
    if p == "openrouter":
        return OpenRouterProvider(model)
    if p == "gpt-oss":
        return LocalGptOssProvider(model)
    return OpenAIProvider(model)


def provider_factory():
    cfg = load_cfg()
    return load_provider(cfg["provider"], cfg["model"])
