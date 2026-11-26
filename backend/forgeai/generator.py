import json
import re
import tempfile
from collections.abc import Callable
from pathlib import Path
from pydantic import TypeAdapter
from . import documents
from .coverage import assess
from .intake import interview
from .llm import ModelClient
from .retrieval import Index
from .schema import Answer, Config, Design, Finding, Passage, Requirements, Selection, Settings
from .tools import REGISTRY, select_tools


def build(brief: str, docs: Path, out: Path, unattended: bool, model: ModelClient, embedding: str, *,
          answer_questions: Callable[[list[str]], dict[str, str]] | None = None,
          approve: Callable[[Requirements, dict[str, Finding]], Requirements] | None = None,
          progress: Callable[[str, str, str], None] | None = None,
          checkpoint: dict | None = None) -> Config:
    def notify(name: str, status: str, detail: str) -> None:
        if progress is not None:
            progress(name, status, detail)

    if out.exists() or out.resolve().is_relative_to(docs.resolve()):
        raise ValueError("Choose a new output directory outside the document folder")
    state = checkpoint if checkpoint is not None else {}
    if "documents" not in state:
        notify("ingestion", "running", f"Reading {docs.name}")
        state["documents"] = documents.load(docs)
        notify("ingestion", "completed", f"Loaded {len(state['documents'][1])} files")
    passages, manifest = state["documents"]
    if "requirements" not in state:
        notify("intake", "running", "Analyzing the brief and documents")
        state["requirements"] = interview(brief, passages, unattended, model, answer_questions=answer_questions)
        notify("intake", "completed", state["requirements"].scope)
    req = state["requirements"].model_copy(deep=True)
    if "approved" in state:
        req, coverage = state["approved"]
        req = req.model_copy(deep=True)
        coverage = {topic: finding.model_copy(deep=True) for topic, finding in coverage.items()}
    else:
        notify("groundability", "running", "Checking document and tool support")
        if "discovery_index" not in state:
            discovery = Settings(chunk_words=100, overlap=20, top_k=6, min_score=0.18)
            discovery_corpus = documents.chunk(passages, discovery)
            state["discovery_index"] = Index(discovery_corpus, discovery, embedding)
        discovery_index = state["discovery_index"]
        coverage = state.get("coverage")
        if coverage is None:
            coverage = assess(req, discovery_index, model)
            state["coverage"] = coverage
        for _ in range(3 if approve else 0):
            approved = approve(req, coverage)
            added = [topic for topic in approved.must_answer if topic not in coverage]
            if added:
                notify("groundability", "running", "Checking the edited topics")
                coverage = coverage | assess(approved.model_copy(update={"must_answer": added}), discovery_index, model)
            coverage = {topic: coverage[topic] for topic in approved.must_answer}
            req = approved
            if not any(coverage[topic].status != "supported" for topic in added):
                break
        else:
            if approve:
                raise ValueError("New limitations must be accepted before generating the agent")
        state["approved"] = (req.model_copy(deep=True),
                             {topic: finding.model_copy(deep=True) for topic, finding in coverage.items()})
        state.pop("discovery_index", None)
        notify("groundability", "completed", f"Checked {len(coverage)} topics")
    notify("generation", "running", "Generating the agent definition")
    req.must_refuse = list(dict.fromkeys([*req.must_refuse, *(t for t, f in coverage.items()
                                     if f.status == "unsupported" and not f.inconclusive)]))
    req.unresolved.extend(f"Document support uncertain: {topic}" for topic, finding in coverage.items()
                          if finding.inconclusive)
    available = set(REGISTRY)
    if not any(p.cells for p in passages):
        available.remove("csv_lookup")
    design = model.ask("design", {"brief": brief, "requirements": req.model_dump(),
                       "files": list(manifest), "coverage": {t: "inconclusive" if f.inconclusive else f.status for t, f in coverage.items()}, "available_tools": sorted(available)}, Design)
    if any(t.name not in available for t in design.tools):
        raise ValueError("Model selected an unavailable tool")
    design.tools = select_tools(design.tools, " ".join([brief, *req.must_answer]))
    explicit_tools = {"csv_lookup": r"\b(?:use|require) (?:exact |the )?csv lookup\b",
                      "calculator": r"\b(?:use|require) (?:the )?calculator\b|\band the calculator\b",
                      "weather": r"\b(?:use|require) (?:the )?(?:open-meteo|weather tool)\b"}
    for name, pattern in explicit_tools.items():
        if name in available and name not in {t.name for t in design.tools} and re.search(pattern, brief, re.I):
            design.tools.append(Selection(name=name, reason="The brief explicitly requests this tool."))
    for tool in dict.fromkeys(finding.tool for finding in coverage.values() if finding.tool):
        if tool not in {t.name for t in design.tools}:
            design.tools.append(Selection(name=tool, reason="Coverage identified this tool as required for a requested function."))
    corpus = documents.chunk(passages, design.settings)
    for finding in coverage.values():
        for quote in finding.evidence:
            source = documents.anchor_id(quote.id)
            quote.id = next((p.id for p in corpus if documents.anchor_id(p.id) == source and quote.quote in p.text), source)
    adapter = TypeAdapter(list[Passage])
    data = adapter.dump_json(corpus)
    sources = adapter.dump_json(passages)
    config = Config(**design.model_dump(), version=1, model=getattr(model, "last_model", model.model), embedding=embedding,
                    requested_model=model.model, generation_models=sorted(getattr(model, "models_used", ()) or [model.model]),
                    behavioral_evaluation=True,
                    requirements=req, coverage=coverage, document_manifest=manifest,
                    output_contract=Answer.model_json_schema(), corpus_sha256=documents.digest(data),
                    sources_sha256=documents.digest(sources))
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as temp:
        stage = Path(temp) / "run"
        stage.mkdir()
        for name, obj in {"requirements": req.model_dump(), "coverage": config.model_dump()["coverage"],
                          "document_manifest": manifest, "agent_config": config.model_dump()}.items():
            (stage / f"{name}.json").write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf8")
        (stage / "corpus.json").write_bytes(data)
        (stage / "sources.json").write_bytes(sources)
        stage.rename(out)
    notify("generation", "completed", f"Saved {out.name}")
    return config

