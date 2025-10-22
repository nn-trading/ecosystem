import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from memory.eventlog import EventLog

def main():
    el = EventLog()
    el.append('log/resummarize', 'runner', {'req': True})

if __name__ == '__main__':
    main()
