from pathlib import Path
import re
from typing import Literal
from pydantic import TypeAdapter
from .documents import chunk, digest
from .llm import make_model
from .retrieval import Index
from .schema import Answer, Config, Model, Passage, Quote, Text, Tool
from .tools import REGISTRY, execute


class Route(Model):
    decision: Literal["answer", "refuse"]
    reason: Text
    tool: Tool | None = None
    arguments: dict = {}


class DocumentRoute(Route):
    """A document-only agent cannot request a tool call."""
    tool: None = None


class CalculatorRoute(Route):
    """After a CSV lookup, only a follow-up calculation is permitted."""
    tool: Literal["calculator"] | None = None


def requests_calculation(question: str) -> bool:
    if re.search(r"\b(?:calculator|calculat\w*|comput\w*|subtotals?|totals?|sum|arithmetic|multiply|divide)\b",
                 question, re.I):
        return True
    quantity = re.search(r"(?<![\w-])\d+(?:\.\d+)?\s+(?!\d)\w+", question)
    return bool(quantity and re.search(r"\b(?:cost|price|quantity|units?|orders?|packs?)\b", question, re.I))


class InvalidCitationError(ValueError):
    pass


class InvalidToolCall(ValueError):
    pass


class ToolTrace(Model):
    name: Tool
    arguments: dict
    results: dict[str, str] = {}


class Execution(Model):
    answer: Answer | None = None
    retrieved: list[Passage] = []
    tools: list[ToolTrace] = []
    error: str | None = None
    invalid_citation: bool = False
    invalid_tool_call: bool = False
    refusal_code: Literal["restricted", "no_evidence"] | None = None


class QuotedAnswer(Answer):
    evidence_quotes: list[Quote]


class Runner:
    def __init__(self, path: Path):
        self.config = Config.model_validate_json(path.read_bytes())
        data = path.with_name("corpus.json").read_bytes()
        if digest(data) != self.config.corpus_sha256:
            raise ValueError("Corpus does not match saved definition")
        adapter = TypeAdapter(list[Passage])
        self.corpus = adapter.validate_json(data)
        self.sources = None
        if self.config.sources_sha256:
            raw = path.with_name("sources.json").read_bytes()
            if digest(raw) != self.config.sources_sha256:
                raise ValueError("Source snapshot does not match saved definition")
            self.sources = adapter.validate_json(raw)
            self.corpus = chunk(self.sources, self.config.settings)
        self.index = Index(self.corpus, self.config.settings, self.config.embedding)
        self.model = make_model(self.config.model)

    def reconfigure(self, config: Config) -> None:
        previous = self.config.settings
        current = config.settings
        if (previous.chunk_words, previous.overlap) != (current.chunk_words, current.overlap):
            if self.sources is None:
                raise ValueError("Rechunking requires an original passage snapshot")
            self.corpus = chunk(self.sources, current)
            self.index.rebuild(self.corpus, current)
        else:
            self.index.settings = current
        self.config = config

    def answer(self, question: str) -> Answer:
        return self._answer(question, Execution())

    def trace(self, question: str) -> Execution:
        trace = Execution()
        try:
            trace.answer = self._answer(question, trace)
        except InvalidCitationError as exc:
            trace.invalid_citation = True
            trace.error = str(exc)
        except InvalidToolCall as exc:
            trace.invalid_tool_call = True
            trace.error = str(exc)
        except (RuntimeError, ValueError, ArithmeticError, OSError) as exc:
            trace.error = f"{type(exc).__name__}: {exc}"
        return trace

    def _explicit_csv_lookup(self, question: str) -> Route | None:
        if not re.search(r"\b(?:csv lookup|look up|lookup)\b", question, re.I):
            return None
        matches = {}
        for passage in self.corpus:
            for column, value in (passage.cells or {}).items():
                if len(value) < 3 or not any(letter.isalpha() for letter in value):
                    continue
                if re.search(rf"(?<!\w){re.escape(value)}(?!\w)", question, re.I):
                    matches.setdefault((passage.file, column, value), set()).add((passage.file, passage.row))
        rows = set().union(*matches.values())
        if len(rows) != 1 or not matches:
            return None
        file, column, value = next(iter(matches))
        return Route(decision="answer", reason="Explicit and unambiguous CSV lookup request",
                     tool="csv_lookup", arguments={"file": file, "column": column, "value": value})

    def _answer(self, question: str, trace: Execution) -> Answer:
        config = self.config
        def refuse(reason: str, code: Literal["restricted", "no_evidence"] | None = None) -> Answer:
            trace.refusal_code = code
            return Answer(answer=reason, citations=[], refused=True)
        banned = [*config.requirements.must_refuse, *(t for t, f in config.coverage.items() if f.status == "unsupported" and not f.inconclusive)]
        if any(t.casefold() in question.casefold() for t in banned):
            return refuse("This topic is restricted by the agent definition.", "restricted")
        allowed = {t.name for t in config.tools}
        context = {"question": question, "requirements": config.requirements.model_dump(),
                   "coverage": {t: ["inconclusive" if f.inconclusive else f.status, f.limitation]
                                for t, f in config.coverage.items()},
                   "agent_guidance": config.system_prompt}
        if "csv_lookup" in allowed:
            context["csv_columns"] = {p.file: list(p.cells) for p in self.corpus if p.cells is not None}
        trace.retrieved = self.index.search(question)
        evidence = {p.id: p.text for p in trace.retrieved}
        if not evidence and not allowed:
            return refuse("No supporting evidence was found.", "no_evidence")
        if config.verify_scope:
            context["scope_review"] = ("Refuse only when the question is outside the declared scope, restricted, "
                                       "or lacks relevant evidence. A paraphrase of a supported topic is in scope.")
        route = self.model.ask("route", {**context, "evidence": evidence,
                               "tools": {n: REGISTRY[n].model_json_schema() for n in allowed}}, Route if allowed else DocumentRoute)
        if route.decision == "refuse":
            return refuse(route.reason)
        deferred_calculation = None
        if route.tool != "csv_lookup" and "csv_lookup" in allowed:
            explicit_lookup = self._explicit_csv_lookup(question)
            if explicit_lookup is not None:
                deferred_calculation = route if route.tool == "calculator" else None
                route = explicit_lookup
        unused = allowed.copy()
        for _ in range(2):
            if not route.tool:
                break
            call = ToolTrace(name=route.tool, arguments=route.arguments)
            trace.tools.append(call)
            if route.tool == "weather":
                for key in ("latitude", "longitude"):
                    value = route.arguments.get(key)
                    numbers = re.findall(r"(?<![\w.])[-+]?\d+(?:\.\d+)?(?![\w.])", question)
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not any(float(n) == value for n in numbers):
                        raise InvalidToolCall("Weather needs explicit coordinates from the question")
            try:
                call.results = execute(route.tool, route.arguments, unused, self.corpus)
            except (ValueError, ArithmeticError) as exc:
                raise InvalidToolCall(str(exc)) from exc
            unused.remove(route.tool)
            if not call.results:
                return refuse("The requested lookup returned no matching rows.")
            evidence.update(call.results)
            if (route.tool != "csv_lookup" or "calculator" not in unused
                    or (deferred_calculation is None and not requests_calculation(question))):
                break
            route = deferred_calculation or self.model.ask("route", {**context, "evidence": evidence, "completed_tools": ["csv_lookup"],
                                   "tools": {"calculator": REGISTRY["calculator"].model_json_schema()}}, CalculatorRoute)
            if route.decision == "refuse":
                return refuse(route.reason)
        if not evidence:
            return refuse("No supporting evidence was found.", "no_evidence")
        # Return trusted arithmetic directly for a single explicit calculation request.
        if ("tool:calculator" in evidence and
                re.search(r"\b(?:use|with) (?:the )?calculator\b", question, re.I) and
                not re.search(r"\b(?:also|plus tell me|and what|and when|and where|and why)\b", question, re.I)):
            ids = [key for call in trace.tools for key in call.results]
            currency = re.search(r"\b(?:in|currency)\s+(USD|EUR|GBP|INR|JPY|CAD|AUD)\b", question, re.I)
            known_units = " ".join(value for key, value in evidence.items() if key != "tool:calculator")
            if not currency or re.search(rf"(?<![A-Z]){currency[1]}(?![A-Z])", known_units, re.I):
                unit = f" {currency[1].upper()}" if currency else ""
                return Answer(answer=f"The calculation result is {evidence['tool:calculator']}{unit}.",
                              citations=list(dict.fromkeys(ids)), refused=False)
        schema = QuotedAnswer if config.evidence_only else Answer
        answer = self.model.ask("answer", {**context, "evidence": evidence}, schema)
        if isinstance(answer, QuotedAnswer) and not answer.refused:
            verified = {q.id for q in answer.evidence_quotes
                        if q.id in evidence and q.quote in evidence[q.id]}
            if not set(answer.citations).issubset(verified):
                return refuse("The answer lacked verifiable excerpts for its citations.")
        if not set(answer.citations).issubset(evidence):
            trace.answer = Answer(answer=answer.answer, citations=answer.citations, refused=answer.refused)
            raise InvalidCitationError("Model cited a source outside retrieved evidence")
        return Answer(answer=answer.answer, citations=answer.citations, refused=answer.refused)

