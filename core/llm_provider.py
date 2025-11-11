from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional

try:
    import openai
except Exception:
    openai = None

@dataclass
class LlmResponse:
    text: str

class LlmProvider:
    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        raise NotImplementedError

class OpenAIProvider(LlmProvider):
    def __init__(self, model: str = "gpt-4o-mini"):
        self.key = os.getenv("OPENAI_API_KEY")
        self.model = model
    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        if not openai or not self.key:
            return "[stubbed openai response] " + prompt[:64]
        client = openai.OpenAI(api_key=self.key)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            chat = client.chat.completions.create(model=self.model, messages=messages, temperature=0.2)
            return chat.choices[0].message.content or ""
        except Exception as e:
            return f"[openai error: {e}]"

class OpenRouterProvider(LlmProvider):
    def __init__(self, model: str = "openrouter/auto"):
        self.key = os.getenv("OPENROUTER_API_KEY")
        self.model = model
    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        if not openai or not self.key:
            return "[stubbed openrouter response] " + prompt[:64]
        # OpenRouter is OpenAI-compatible in many SDKs
        client = openai.OpenAI(api_key=self.key, base_url="https://openrouter.ai/api/v1")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            chat = client.chat.completions.create(model=self.model, messages=messages, temperature=0.2)
            return chat.choices[0].message.content or ""
        except Exception as e:
            return f"[openrouter error: {e}]"

class LocalGptOssProvider(LlmProvider):
    def __init__(self, model: str = "openai/gpt-oss-20b"):
        # Placeholder stub; full HF model load is heavy and not required for smoke
        self.model = model
    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        return "[local gpt-oss stub] " + prompt[:80]

PROVIDERS = {
    "openai": OpenAIProvider,
    "openrouter": OpenRouterProvider,
    "gpt-oss": LocalGptOssProvider,
}

def load_provider(provider: str, model: str) -> LlmProvider:
    cls = PROVIDERS.get(provider)
    if not cls:
        return LocalGptOssProvider(model=model)
    return cls(model=model)
