import json, sys, time
sys.path.append(r'C:\bots\ecosys')
import brain_orchestrator as bo

print('OPEN', json.dumps(bo.run_action('app_open', {'name':'notepad.exe'}), ensure_ascii=False))
time.sleep(0.8)
print('FOCUS', json.dumps(bo.run_action('app_focus', {'title':'notepad'}), ensure_ascii=False))
time.sleep(0.3)
print('TYPE', json.dumps(bo.run_action('type', {'text':'Ecosys GUI type OK', 'enter': True, 'delay': 0.02}), ensure_ascii=False))
time.sleep(0.5)
print('CLOSE', json.dumps(bo.run_action('app_close', {'name':'notepad.exe'}), ensure_ascii=False))
