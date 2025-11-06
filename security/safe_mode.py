_scopes = set()
_enabled = False

def set_scopes(scopes):
    global _scopes
    _scopes = set(scopes or [])

def enable():
    global _enabled
    _enabled = True

def disable():
    global _enabled
    _enabled = False

def status():
    return {'enabled': _enabled, 'scopes': sorted(list(_scopes))}
