from collections import deque
_q = deque()

def publish(x):
    _q.append(x)

def subscribe():
    while _q:
        yield _q.popleft()

def smoke():
    publish({'k':'v'})
    return next(subscribe(), None) is not None
