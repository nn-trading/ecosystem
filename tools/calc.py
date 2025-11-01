# C:\bots\ecosys\tools\calc.py
from __future__ import annotations

import ast
from typing import Any, Dict

_ALLOWED_NODES = (
    ast.Expression,
    ast.UnaryOp,
    ast.BinOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
    ast.Load,
    ast.Constant,
    ast.Tuple,
)


def _safe_eval(node: ast.AST) -> float:
    if not isinstance(node, _ALLOWED_NODES):
        raise ValueError(f"disallowed: {type(node).__name__}")
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError("constants other than numbers not allowed")
    if isinstance(node, ast.UnaryOp):
        v = _safe_eval(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +v
        if isinstance(node.op, ast.USub):
            return -v
        raise ValueError("unary op not allowed")
    if isinstance(node, ast.BinOp):
        a = _safe_eval(node.left)
        b = _safe_eval(node.right)
        if isinstance(node.op, ast.Add):
            return a + b
        if isinstance(node.op, ast.Sub):
            return a - b
        if isinstance(node.op, ast.Mult):
            return a * b
        if isinstance(node.op, ast.Div):
            return a / b
        if isinstance(node.op, ast.FloorDiv):
            return a // b
        if isinstance(node.op, ast.Mod):
            return a % b
        if isinstance(node.op, ast.Pow):
            return a ** b
        raise ValueError("binary op not allowed")
    raise ValueError("unsupported expression")


def calc_eval(expr: str) -> Dict[str, Any]:
    try:
        if not isinstance(expr, str) or not expr.strip():
            return {"ok": False, "error": "empty expression"}
        parsed = ast.parse(expr, mode="eval")
        res = _safe_eval(parsed)
        return {"ok": True, "result": res}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def register(reg) -> None:
    reg.add("calc.eval", calc_eval, desc="Evaluate arithmetic expression -> {ok,result}")
