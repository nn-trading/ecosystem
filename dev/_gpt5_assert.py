import json, pathlib, re, os
ROOT = pathlib.Path(__file__).resolve().parents[1]
cfg = (ROOT/'configs'/'model.yaml').read_text(errors='ignore')
locked = bool(re.search(r'(?im)^\s*lock\s*:\s*(true|True|1)', cfg))
m = re.search(r'(?im)^\s*default\s*:\s*([^\r\n#]+)', cfg)
model = (m.group(1).strip().strip('"\'')) if m else 'gpt-5'
out = ROOT/'reports'/'GPT5_ASSERT.json'
out.write_text(json.dumps({'default':model,'locked':locked}, indent=2), encoding='utf-8')
print(json.dumps({'default':model,'locked':locked}))
