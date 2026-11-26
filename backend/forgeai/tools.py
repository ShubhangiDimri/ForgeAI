from datetime import datetime, timezone
from decimal import Decimal
import json
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, build_opener
from urllib.error import URLError
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


class Component(Model):
    label: Text
    value: Decimal = Field(max_digits=16, decimal_places=6, allow_inf_nan=False)
    source: Text
    quote: Text


class SumPlan(Model):
    operation: Literal["sum"]
    components: list[Component] = Field(min_length=2, max_length=12)
    unit: str = Field(default="", max_length=20)


class NoArgs(Model):
    pass


class Weather(Model):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)


class CurrentWeather(Model):
    time: Text
    temperature_2m: float = Field(allow_inf_nan=False)
    wind_speed_10m: float = Field(ge=0, allow_inf_nan=False)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


REGISTRY = {"csv_lookup": Lookup, "calculator": Arithmetic, "current_date": NoArgs, "weather": Weather}


def numeric_values(text: str) -> set[Decimal]:
    return {Decimal(match.replace(",", "")) for match in re.findall(
        r"(?<![\w.])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?!\w|\.\d)", text)}


def verified_sum(arguments: dict, evidence: dict[str, str]) -> tuple[SumPlan, str]:
    plan = SumPlan.model_validate(arguments)
    seen = set()
    for component in plan.components:
        key = (component.source, component.quote, component.value)
        quote = " ".join(component.quote.split())
        if (key in seen or component.source.startswith("tool:")
                or quote not in " ".join(evidence.get(component.source, "").split())
                or component.value not in numeric_values(component.quote)):
            raise ValueError("A calculation component lacks a distinct supporting source quotation")
        seen.add(key)
    if plan.unit and not any(re.search(rf"(?<!\w){re.escape(plan.unit)}(?!\w)", text, re.I)
                             for key, text in evidence.items() if not key.startswith("tool:")):
        raise ValueError("The calculation unit is not stated in source evidence")
    return plan, str(sum(c.value for c in plan.components))


def current_weather(args: Weather) -> dict[str, str]:
    query = urlencode({**args.model_dump(), "current": "temperature_2m,wind_speed_10m", "timezone": "UTC"})
    url = "https://api.open-meteo.com/v1/forecast?" + query
    try:
        with build_opener(NoRedirect()).open(url, timeout=8) as response:
            body = response.read(32769)
        if len(body) > 32768:
            raise ValueError("Weather response exceeds size limit")
        data = CurrentWeather.model_validate({k: v for k, v in json.loads(body)["current"].items()
                                             if k in CurrentWeather.model_fields})
    except (URLError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise RuntimeError(f"Open-Meteo lookup failed: {exc}") from exc
    text = f"Open-Meteo at {data.time} UTC: {data.temperature_2m} C, wind {data.wind_speed_10m} km/h"
    return {"tool:weather": text}


def execute(name: str, arguments: dict, allowed: set[str], corpus: list[Passage]) -> dict[str, str]:
    if name not in allowed or name not in REGISTRY:
        raise ValueError(f"Tool not permitted: {name}")
    args = REGISTRY[name].model_validate(arguments)
    if isinstance(args, Lookup):
        return {p.id: p.text for p in corpus if p.file == args.file and p.cells is not None
                and p.cells.get(args.column) == args.value}
    if isinstance(args, Arithmetic):
        operations = dict(add=operator.add, subtract=operator.sub, multiply=operator.mul, divide=operator.truediv)
        result = operations[args.operation](Decimal(str(args.left)), Decimal(str(args.right)))
        if not math.isfinite(result):
            raise ValueError("Result outside numeric range")
        value = format(result.normalize(), "f")
        return {"tool:calculator": value if "." in value else value + ".0"}
    if isinstance(args, Weather):
        return current_weather(args)
    return {"tool:current_date": datetime.now(timezone.utc).date().isoformat() + " (UTC)"}


def select_tools(proposals: list[Selection], intent: str) -> list[Selection]:
    # Require evidence of a requested capability as well as model selection.

    capabilities = {
        "csv_lookup": r"\b(look\s?up|lookup|search|find|catalog(?:ue)?|inventory|directory|tabular|csv|spreadsheet)\b",
        "calculator": r"\b(calculat\w*|comput\w*|arithmetic|total\w*|sum|convert\w*|estim\w*|average|percentage)\b",
        "weather": r"\b(weather|forecast|wind conditions)\b",
        "current_date": r"\b(today\w*|current date|as of now|days until|days since)\b",
    }
    selected = {tool.name: tool for tool in proposals if re.search(capabilities[tool.name], intent, re.I)}
    return list(selected.values())
