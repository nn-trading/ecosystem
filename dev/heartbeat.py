import asyncio, time, json, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from memory.eventlog import EventLog

async def main(period=5.0):
    log = EventLog()
    while True:
        try:
            payload = {
                'ts': time.time(),
                'pid': os.getpid(),
                'src': 'heartbeat',
            }
            log.append('system/heartbeat', 'heartbeat', payload)
        except Exception:
            pass
        await asyncio.sleep(period)

if __name__ == '__main__':
    try:
        period = float(os.environ.get('HEARTBEAT_SEC', '5.0'))
    except Exception:
        period = 5.0
    asyncio.run(main(period))
