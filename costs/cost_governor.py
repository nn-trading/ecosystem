_state={'daily_cap': 5.0}

def set_daily_cap(x: float):
    _state['daily_cap']=float(x)

def status():
    return dict(_state)
