from core.intent import parse_intent, plan_steps, Intent

def test_parse_intent_basic():
    i = parse_intent("goal: build a logger; constraint: ascii only; success: tests green")
    assert isinstance(i, Intent)
    assert "logger" in i.goal
    assert "ascii only" in i.constraints[0].lower()
    assert any("tests" in s for s in i.success)

def test_plan_steps_echo():
    i = Intent(goal="ship feature", constraints=["ascii"], success=["tests passed"])
    steps = plan_steps(i)
    assert steps and steps[0]["action"] == "plan"
    assert "ship feature" in steps[0]["description"]
