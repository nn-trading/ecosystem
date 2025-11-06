def check_action(action: str):
    if 'registry' in action.lower():
        return {'allowed': False, 'reason': 'high_risk'}
    return {'allowed': True}
