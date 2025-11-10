import importlib.util, json, os
p = r'C:\bots\ecosys\brain_orchestrator.py'
spec = importlib.util.spec_from_file_location('bo', p)
bo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bo)
print(json.dumps({'ALLOWED_TOOLS': sorted(list(bo.ALLOWED_TOOLS))}))
print(json.dumps({'SCHEMA_has_press': ('press' in bo.SCHEMA), 'SCHEMA_has_file_download': ('file_download' in bo.SCHEMA), 'SCHEMA_has_hotkey': ('hotkey' in bo.SCHEMA)}))
os.makedirs(r'C:\bots\ecosys\reports\proofs', exist_ok=True)
try:
    res1 = bo.run_action('press', {'keys':'enter', 'interval': 0.05})
except Exception as e:
    res1 = {'ok': False, 'error': str(e)}
print(json.dumps({'press': res1}, ensure_ascii=False))
try:
    res2 = bo.run_action('file_download', {'url':'https://example.com', 'out': r'C:\bots\ecosys\reports\proofs\example2.html', 'timeout': 30})
except Exception as e:
    res2 = {'ok': False, 'error': str(e)}
print(json.dumps({'file_download': res2}, ensure_ascii=False))
