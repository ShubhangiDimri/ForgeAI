from pathlib import Path
import re
from typing import Literal
from pydantic import TypeAdapter
from .documents import chunk, digest
from .llm import Ollama
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


class InvalidCitationError(ValueError):
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
        self.model = Ollama(self.config.model)

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
        except (RuntimeError, ValueError, ArithmeticError, OSError) as exc:
            trace.error = f"{type(exc).__name__}: {exc}"
        return trace

    def _answer(self, question: str, trace: Execution) -> Answer:
        config = self.config
        def refuse(reason: str) -> Answer:
            return Answer(answer=reason, citations=[], refused=True)
        banned = [*config.requirements.must_refuse, *(t for t, f in config.coverage.items() if f.status == "unsupported" and not f.inconclusive)]
        if any(t.casefold() in question.casefold() for t in banned):
            return refuse("This topic is restricted by the agent definition.")
        allowed = {t.name for t in config.tools}
        context = {"question": question, "requirements": config.requirements.model_dump(),
                   "coverage": {t: [f.status, f.limitation] for t, f in config.coverage.items()},
                   "agent_guidance": config.system_prompt}
        if "csv_lookup" in allowed:
            context["csv_columns"] = {p.file: list(p.cells) for p in self.corpus if p.cells is not None}
        trace.retrieved = self.index.search(question)
        evidence = {p.id: p.text for p in trace.retrieved}
        if not evidence and not allowed:
            return refuse("No supporting evidence was found.")
        if config.verify_scope:
            context["scope_review"] = ("Refuse only when the question is outside the declared scope, restricted, "
                                       "or lacks relevant evidence. A paraphrase of a supported topic is in scope.")
        route = self.model.ask("route", {**context, "evidence": evidence,
                               "tools": {n: REGISTRY[n].model_json_schema() for n in allowed}}, Route if allowed else DocumentRoute)
        if route.decision == "refuse":
            return refuse(route.reason)
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
                        raise ValueError("Weather needs explicit coordinates from the question")
            call.results = execute(route.tool, route.arguments, unused, self.corpus)
            unused.remove(route.tool)
            if not call.results:
                return refuse("The requested lookup returned no matching rows.")
            evidence.update(call.results)
            if route.tool != "csv_lookup" or "calculator" not in unused:
                break
            route = self.model.ask("route", {**context, "evidence": evidence, "completed_tools": ["csv_lookup"],
                                   "tools": {"calculator": REGISTRY["calculator"].model_json_schema()}}, Route)
            if route.decision == "refuse":
                return refuse(route.reason)
        if not evidence:
            return refuse("No supporting evidence was found.")
        schema = QuotedAnswer if config.evidence_only else Answer
        answer = self.model.ask("answer", {**context, "evidence": evidence}, schema)
        if isinstance(answer, QuotedAnswer) and not answer.refused:
            verified = {q.id for q in answer.evidence_quotes
                        if q.id in evidence and q.quote in evidence[q.id]}
            if not set(answer.citations).issubset(verified):
                return refuse("The answer lacked verifiable excerpts for its citations.")
        if not set(answer.citations).issubset(evidence):
            raise InvalidCitationError("Model cited a source outside retrieved evidence")
        return Answer(answer=answer.answer, citations=answer.citations, refused=answer.refused)

