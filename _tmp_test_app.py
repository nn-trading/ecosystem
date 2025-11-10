import json, sys
sys.path.append(r'C:\bots\ecosys')
import brain_orchestrator as bo
print(json.dumps(bo.run_action('app_list', {'filter':'powershell'}), ensure_ascii=False))
