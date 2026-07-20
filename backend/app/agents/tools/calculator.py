"""Calculator tool — evaluates arithmetic safely via the ``ast`` module.

No ``eval`` is used. The expression is parsed to an AST and only a small,
explicitly whitelisted set of numeric operations is permitted, so untrusted
input can never execute arbitrary code.
"""

from __future__ import annotations

import ast
import math
import operator
from typing import Any

from app.agents.tools.base import Tool, ToolContext, ToolError

# Whitelisted binary / unary operators.
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Whitelisted named constants and single-argument functions.
_NAMES = {"pi": math.pi, "e": math.e, "tau": math.tau}
_FUNCS = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
    "log": math.log,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
}


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ToolError("Only numeric literals are allowed")
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.Name) and node.id in _NAMES:
        return _NAMES[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fn = _FUNCS.get(node.func.id)
        if fn is None:
            raise ToolError(f"Unknown function: {node.func.id}")
        args = [_eval_node(a) for a in node.args]
        return fn(*args)
    raise ToolError("Unsupported or unsafe expression")


def safe_eval(expression: str) -> float:
    """Parse and evaluate an arithmetic expression, or raise ToolError."""
    if not isinstance(expression, str) or not expression.strip():
        raise ToolError("expression must be a non-empty string")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ToolError(f"Invalid expression: {exc.msg}") from exc
    result = _eval_node(tree)
    return result


def _run(params: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    expression = params.get("expression", "")
    value = safe_eval(expression)
    # Present whole-number floats as ints for a cleaner result.
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return {"expression": expression, "result": value}


calculator_tool = Tool(
    name="calculator",
    description="Evaluate an arithmetic expression safely (supports + - * / ** %, "
    "sqrt, sin, cos, log, pi, e).",
    parameters={"expression": "The arithmetic expression to evaluate, e.g. '2 * (3 + 4)'"},
    run=_run,
    examples=["2 + 2", "sqrt(144)", "3 * (10 - 4) / 2"],
)
