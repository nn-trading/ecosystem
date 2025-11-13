import os, json, time
from requests.sessions import Session
from requests import RequestException

LOG = r"C:\bots\ecosys\reports\llm\responses_debug.jsonl"
def _log(obj):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception:
        pass

_orig_request = Session.request

def _typed_messages(msgs):
    out = []
    allowed = {"input_text","input_image","output_text","refusal","input_file","computer_screenshot","summary_text"}
    for m in (msgs or []):
        role = m.get("role", "user")
        content = m.get("content", "")
        parts = []
        if isinstance(content, str):
            parts = [{"type": "input_text", "text": content}]
        elif isinstance(content, list):
            for p in content:
                if isinstance(p, dict):
                    t = p.get("type")
                    if t == "text":
                        parts.append({"type": "input_text", "text": p.get("text", "")})
                    elif t in allowed:
                        parts.append(p)
                    elif "text" in p:
                        parts.append({"type": "input_text", "text": p.get("text", "")})
                    else:
                        parts.append({"type": "input_text", "text": str(p)})
                else:
                    parts.append({"type": "input_text", "text": str(p)})
        else:
            parts = [{"type": "input_text", "text": str(content)}]
        out.append({"role": role, "content": parts})
    return out

def _coerce_payload(kwargs):
    body = kwargs.get("json")
    if body is None and "data" in kwargs and isinstance(kwargs["data"], (str, bytes)):
        try: body = json.loads(kwargs["data"])
        except Exception: body = None
    if not isinstance(body, dict): body = {}
    return body

# Strict drop of unsupported fields for GPT-5 Responses API
# Remove fields that are not accepted by /v1/responses for gpt-5 models.
# Extend this list as needed based on server errors observed in debug logs.
def _drop_unsupported_fields(d: dict) -> dict:
    try:
        if isinstance(d, dict):
            for k in ("temperature","top_p","top_k","n","logprobs"):
                d.pop(k, None)
    except Exception:
        pass
    return d

def _patch_request(self, method, url, **kwargs):
    try:
        if method.upper()=="POST" and "api.openai.com" in url:
            body = _coerce_payload(kwargs)
            model = body.get("model") or os.getenv("OPENAI_MODEL") or ""
            # Upgrade legacy Chat Completions -> Responses for GPT-5*
            if "/v1/chat/completions" in url and model.startswith("gpt-5"):
                url = "https://api.openai.com/v1/responses"
                msg = _typed_messages(body.get("messages") or [])
                new = {"model": model, "input": msg}
                if "max_tokens" in body:  new["max_output_tokens"] = body["max_tokens"]
                if "tools" in body:       new["tools"] = body["tools"]
                if "response_format" in body: new["response_format"]= body["response_format"]
                kwargs["json"] = _drop_unsupported_fields(new)
                kwargs.pop("data", None)
            elif "/v1/responses" in url and model.startswith("gpt-5"):
                # sanitize any direct Responses calls
                new = {}
                # model
                new["model"] = model
                # input/messages coercion
                if "messages" in body and "input" not in body:
                    new["input"] = _typed_messages(body.get("messages") or [])
                else:
                    inp = body.get("input")
                    if isinstance(inp, str):
                        new["input"] = [{"role":"user","content":[{"type":"input_text","text": inp}]}]
                    elif isinstance(inp, list):
                        new["input"] = _typed_messages(inp)
                    else:
                        new["input"] = [{"role":"user","content":[{"type":"input_text","text": ""}]}]
                # allowed optional fields
                if isinstance(body, dict) and "max_tokens" in body:
                    new["max_output_tokens"] = body["max_tokens"]
                if isinstance(body, dict) and "max_output_tokens" in body:
                    new["max_output_tokens"] = body["max_output_tokens"]
                if isinstance(body, dict) and "tools" in body:
                    new["tools"] = body["tools"]
                if isinstance(body, dict) and "response_format" in body:
                    new["response_format"] = body["response_format"]
                # finalize (strict drop of unsupported fields like temperature)
                kwargs["json"] = _drop_unsupported_fields(new)
                kwargs.pop("data", None)
    except Exception as e:
        _log({"ts":time.time(),"shim":"pre","err":repr(e)})

    resp = _orig_request(self, method, url, **kwargs)
    try:
        if resp.status_code < 400:
            # For GPT-5 Responses, convert to chat-completions-like payload for backward compat
            if "api.openai.com" in (getattr(resp, 'url', '') or '') and "/v1/responses" in (getattr(resp, 'url', '') or '') and (model or '').startswith("gpt-5"):
                try:
                    data = resp.json()
                    # Responses may return either `content` (list of typed parts),
                    # or a chat-like `output` with `message` having `content` list.
                    parts = data.get("content")
                    if not parts and isinstance(data.get("output"), dict):
                        # OpenAI Responses often nests under output.message.content
                        msg = data.get("output", {}).get("message", {})
                        parts = msg.get("content")
                    if not parts:
                        parts = data.get("output") or []
                    text_out = ""
                    def _collect_text(pt):
                        nonlocal text_out
                        if isinstance(pt, dict):
                            # Recurse into nested message/content structures
                            if isinstance(pt.get("content"), list):
                                for q in pt.get("content"):
                                    _collect_text(q)
                            t = pt.get("type")
                            # common typed content entries and generic text holders
                            if t in ("output_text","input_text","summary_text","text") and "text" in pt:
                                text_out += pt.get("text", "")
                            elif "text" in pt and isinstance(pt["text"], str):
                                text_out += pt["text"]
                        elif isinstance(pt, str):
                            text_out += pt
                    if isinstance(parts, list):
                        for p in parts:
                            _collect_text(p)
                    elif isinstance(parts, dict):
                        # some variants wrap content as dict with nested arrays
                        for v in parts.values():
                            if isinstance(v, list):
                                for p in v: _collect_text(p)
                            else:
                                _collect_text(v)
                    elif isinstance(parts, str):
                        text_out = parts
                    patched = {
                        "id": data.get("id"),
                        "object": "chat.completion",
                        "model": data.get("model") or (model or ""),
                        "choices": [{"message": {"role": "assistant", "content": text_out}}],
                        "via_responses": True,
                    }
                    resp._content = json.dumps(patched).encode("utf-8")
                    resp.headers["Content-Type"] = "application/json"
                except Exception as e:
                    _log({"ts":time.time(),"shim":"post_ok","warn":"patch_resp_failed","err":repr(e)})
        else:
            body = _coerce_payload(kwargs)
            text = resp.text[:4000]
            _log({"ts":time.time(),"url":url,"status":resp.status_code,"model":(body.get("model") if isinstance(body,dict) else None),"req":body,"resp":text})
    except Exception as e:
        _log({"ts":time.time(),"shim":"post","err":repr(e)})
    return resp

# Apply once
if not getattr(Session, "_gpt5_responses_shim", False):
    Session.request = _patch_request
    Session._gpt5_responses_shim = True
