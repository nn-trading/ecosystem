import json, requests, sys
sys.path.append(r'C:\bots\ecosys')
import core.patch_openai_responses  # ensure shim loads

url = 'https://api.openai.com/v1/chat/completions'
headers = {
    'Authorization': 'Bearer INVALID_KEY',
    'Content-Type': 'application/json'
}
body = {
    'model': 'gpt-5',
    'messages': [
        {'role':'user','content':'hello from shim test'}
    ],
    'temperature': 0.4,
    'max_tokens': 64
}

try:
    r = requests.post(url, headers=headers, data=json.dumps(body), timeout=15)
    print('status', r.status_code)
    print((r.text or '')[:200])
except Exception as e:
    print('exc', e)
