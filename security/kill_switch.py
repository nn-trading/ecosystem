_state = {'armed': False}

def arm():
    _state['armed'] = True

def disarm():
    _state['armed'] = False

def is_armed():
    return bool(_state['armed'])
