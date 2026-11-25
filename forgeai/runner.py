from pathlib import Path
from typing import Literal
from pydantic import TypeAdapter
from .documents import digest
from .llm import Ollama
from .retrieval import Index
from .schema import Answer, Config, Model, Passage, Text, Tool
from .tools import REGISTRY, execute


class Route(Model):
    decision: Literal["answer", "refuse"]
    reason: Text
    tool: Tool | None = None
    arguments: dict = {}


class DocumentRoute(Route):
    """A document-only agent cannot request a tool call."""
    tool: None = None


class Runner:
    def __init__(self, path: Path):
        self.config = Config.model_validate_json(path.read_bytes())
        data = path.with_name("corpus.json").read_bytes()
        if digest(data) != self.config.corpus_sha256:
            raise ValueError("Corpus does not match saved definition")
        self.corpus = TypeAdapter(list[Passage]).validate_json(data)
        self.index = Index(self.corpus, self.config.settings, self.config.embedding)
        self.model = Ollama(self.config.model)

    def answer(self, question: str) -> Answer:
        config = self.config
        def refuse(reason: str) -> Answer:
            return Answer(answer=reason, citations=[], refused=True)
        banned = [*config.requirements.must_refuse, *(t for t, f in config.coverage.items() if f.status == "unsupported")]
        if any(t.casefold() in question.casefold() for t in banned):
            return refuse("This topic is restricted by the agent definition.")
        allowed = {t.name for t in config.tools}
        context = {"question": question, "requirements": config.requirements.model_dump(),
                   "coverage": {t: [f.status, f.limitation] for t, f in config.coverage.items()},
                   "agent_guidance": config.system_prompt}
        evidence = {p.id: p.text for p in self.index.search(question)}
        route = self.model.ask("route", {**context, "evidence": evidence,
                               "tools": {n: REGISTRY[n].model_json_schema() for n in allowed}}, Route if allowed else DocumentRoute)
        if route.decision == "refuse":
            return refuse(route.reason)
        if route.tool:
            results = execute(route.tool, route.arguments, allowed, self.corpus)
            if not results:
                return refuse("The requested lookup returned no matching rows.")
            evidence.update(results)
        if not evidence:
            return refuse("No supporting evidence was found.")
        answer = self.model.ask("answer", {**context, "evidence": evidence}, Answer)
        if not set(answer.citations).issubset(evidence):
            raise ValueError("Model cited a source outside retrieved evidence")
        return answer

