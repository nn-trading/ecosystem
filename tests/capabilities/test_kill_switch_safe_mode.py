from security import kill_switch as ks
from security import safe_mode as sm

def test_kill_switch_arm_disarm():
    ks.arm(); assert ks.is_armed(); ks.disarm(); assert not ks.is_armed()

def test_safe_mode_scopes():
    sm.set_scopes(['file','net']); sm.enable(); st=sm.status(); assert st['enabled'] and 'file' in st['scopes']
