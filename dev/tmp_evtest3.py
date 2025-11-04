from pathlib import Path
import sys, json
ROOT=Path(r"C:\\bots\\ecosys")
DEV=ROOT/"dev"
sys.path.insert(0,str(DEV))
sys.path.insert(0,str(ROOT))
from memory.eventlog import EventLog

# Insert a payload containing quotes and spaces and colon
EventLog().append('core/test_ascii','tester',{'msg':'he said "quotes" and colon:a and spaced term'})
print(json.dumps(EventLog().search('quotes',5)))
print(json.dumps(EventLog().search('"quotes"',5)))
print(json.dumps(EventLog().search('colon:a',5)))
print(json.dumps(EventLog().search('spaced term',5)))
