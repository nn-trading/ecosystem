from pathlib import Path
import sys, json
ROOT=Path(r"C:\\bots\\ecosys")
DEV=ROOT/"dev"
sys.path.insert(0,str(DEV))
sys.path.insert(0,str(ROOT))
from memory.eventlog import EventLog
ev=EventLog()
ev.append('core/test_ascii','tester',{'msg':'hello symbols : / \\ " quotes'})
print(json.dumps(ev.search('core/test_ascii',5)))
