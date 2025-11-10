import json
from dev import local_tools as t
print(json.dumps({'monitors': t.count_monitors()}))
print(json.dumps({'windows': t.count_windows()}))
print(json.dumps({'screenshot': bool(t.screenshot())}))
print(json.dumps(t.forecast_budapest_to_desktop(3)))