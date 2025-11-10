import json
from pathlib import Path
from .local_tools import (
    count_monitors, count_windows,
    screenshot_autoname, desktop_write_autoname,
    notepad_save_text_autoname
)
ROOT=Path(__file__).resolve().parents[1]; RPTS=ROOT/'reports'
RPTS.mkdir(parents=True, exist_ok=True)
out={}
out['monitors']=count_monitors(); out['windows']=count_windows()
out['desktop_write']=desktop_write_autoname('OK','e2e_probe')
out['notepad_saved']=notepad_save_text_autoname('E2E NOTEPAD OK','e2e_notepad')
out['screenshot']=screenshot_autoname('e2e')
(RPTS/'AUTONAME_OK.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print(json.dumps(out))
