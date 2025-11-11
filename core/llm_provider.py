from __future__ import annotations
import os, pathlib
from dataclasses import dataclass
from typing import Optional

import yaml
import httpx

try:
    import openai
except Exception:
    openai = None

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG  = ROOT / "config" / "llm.yaml"

def load_cfg() -> dict:
    try:
        raw = CFG.read_text(encoding='utf-8')
    except Exception:
        return {'provider': 'openai', 'model': 'gpt-5'}
    try:
        data = yaml.safe_load(raw) or {}
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    if 'provider' not in data:
        data['provider'] = 'openai'
    if 'model' not in data:
        data['model'] = 'gpt-5'
    return data

@dataclass
class LlmResponse:
    text: str

class LlmProvider:
    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        raise NotImplementedError

class OpenAIProvider(LlmProvider):
    def __init__(self, model: str = 'gpt-4o-mini'):
        self.key = os.getenv('OPENAI_API_KEY')
        self.model = model
    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        if not openai or not self.key:
            return '[stubbed openai response] ' + ((prompt[:64]) if prompt else '')
        try:
            client = openai.OpenAI(api_key=self.key)
            messages = []
            if system:
                messages.append({'role': 'system', 'content': system})
            messages.append({'role': 'user', 'content': prompt})
            chat = client.chat.completions.create(model=self.model, messages=messages, temperature=0.2)
            return chat.choices[0].message.content or ''
        except Exception as e:
            return f'[openai error: {e}]'

class OpenRouterProvider(LlmProvider):
    def __init__(self, model: str = 'openrouter/auto'):
        self.key = os.getenv('OPENROUTER_API_KEY') or ''
        self.model = model
    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        if not self.key:
            return '[stubbed openrouter response] ' + ((prompt[:64]) if prompt else '')
        msgs = []
        if system:
            msgs.append({'role': 'system', 'content': system})
        msgs.append({'role': 'user', 'content': prompt})
        headers = {
            'Authorization': f'Bearer {self.key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://github.com/nn-trading/ecosystem',
            'X-Title': 'Ecosystem AI',
        }
        payload = {'model': self.model, 'messages': msgs}
        try:
            r = httpx.post('https://openrouter.ai/api/v1/chat/completions', headers=headers, json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            return (data.get('choices', [{}])[0].get('message', {}) or {}).get('content', '') or ''
        except Exception as e:
            return f'[openrouter error: {e}]'

class LocalGptOssProvider(LlmProvider):
    def __init__(self, model: str = 'openai/gpt-oss-20b'):
        self.model = model
    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        return '[local gpt-oss stub] ' + ((prompt[:80]) if prompt else '')

PROVIDERS = {
    'openai': OpenAIProvider,
    'openrouter': OpenRouterProvider,
    'gpt-oss': LocalGptOssProvider,
}

def load_provider(provider: str, model: str) -> LlmProvider:
    cls = PROVIDERS.get((provider or '').lower())
    if not cls:
        return LocalGptOssProvider(model=model)
    return cls(model=model)

def provider_factory() -> LlmProvider:
    cfg = load_cfg()
    prov = str(cfg.get('provider', 'openai'))
    model = str(cfg.get('model', 'gpt-5'))
    return load_provider(prov, model)
