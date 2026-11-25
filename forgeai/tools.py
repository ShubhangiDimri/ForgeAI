from datetime import date
import math
import operator
import re
from typing import Literal
from pydantic import Field
from .schema import Model, Passage, Selection, Text


class Lookup(Model):
    file: Text
    column: Text
    value: Text


class Arithmetic(Model):
    operation: Literal["add", "subtract", "multiply", "divide"]
    left: float = Field(allow_inf_nan=False)
    right: float = Field(allow_inf_nan=False)


class NoArgs(Model):
    pass


REGISTRY = {"csv_lookup": Lookup, "calculator": Arithmetic, "current_date": NoArgs}


def execute(name: str, arguments: dict, allowed: set[str], corpus: list[Passage]) -> dict[str, str]:
    if name not in allowed or name not in REGISTRY:
        raise ValueError(f"Tool not permitted: {name}")
    args = REGISTRY[name].model_validate(arguments)
    if isinstance(args, Lookup):
        return {p.id: p.text for p in corpus if p.file == args.file and p.cells is not None
                and p.cells.get(args.column) == args.value}
    if isinstance(args, Arithmetic):
        operations = dict(add=operator.add, subtract=operator.sub, multiply=operator.mul, divide=operator.truediv)
        result = operations[args.operation](args.left, args.right)
        if not math.isfinite(result):
            raise ValueError("Result outside numeric range")
        return {"tool:calculator": str(result)}
    return {"tool:current_date": date.today().isoformat()}


def select_tools(proposals: list[Selection], intent: str) -> list[Selection]:
    # Require evidence of a requested capability as well as model selection.

    capabilities = {
        "csv_lookup": r"\b(look\s?up|lookup|search|find|catalog(?:ue)?|inventory|directory|tabular|csv|spreadsheet)\b",
        "calculator": r"\b(calculat\w*|comput\w*|arithmetic|total\w*|sum|convert\w*|estim\w*|average|percentage)\b",
        "current_date": r"\b(today\w*|current date|as of now|days until|days since)\b",
    }
    return [tool for tool in proposals if re.search(capabilities[tool.name], intent, re.I)]
