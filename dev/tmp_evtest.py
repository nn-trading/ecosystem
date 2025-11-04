from memory.eventlog import EventLog
import json

ev=EventLog()
ev.append('core/test_ascii','tester',{'msg':'hello symbols : / \\ " quotes'})
print(json.dumps(ev.search('core/test_ascii',5)))
