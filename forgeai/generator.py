import json
import re
import tempfile
from pathlib import Path
from pydantic import TypeAdapter
from . import documents
from .coverage import assess
from .intake import interview
from .llm import ModelClient
from .retrieval import Index
from .schema import Answer, Config, Design, Passage, Selection, Settings
from .tools import REGISTRY, select_tools


def build(brief: str, docs: Path, out: Path, unattended: bool, model: ModelClient, embedding: str) -> Config:
    if out.exists() or out.resolve().is_relative_to(docs.resolve()):
        raise ValueError("Choose a new output directory outside the document folder")
    passages, manifest = documents.load(docs)
    req = interview(brief, passages, unattended, model)
    discovery = Settings(chunk_words=100, overlap=20, top_k=6, min_score=0.18)
    discovery_corpus = documents.chunk(passages, discovery)
    discovery_index = Index(discovery_corpus, discovery, embedding)
    coverage = assess(req, discovery_index, model)
    req.must_refuse = list(dict.fromkeys([*req.must_refuse, *(t for t, f in coverage.items()
                                     if f.status == "unsupported" and not f.inconclusive)]))
    req.unresolved.extend(f"Document support uncertain: {topic}" for topic, finding in coverage.items()
                          if finding.inconclusive)
    # Store source locators independent of the final design's chunk sizes.
    for finding in coverage.values():
        for quote in finding.evidence:
            quote.id = documents.anchor_id(quote.id)
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
    corpus = documents.chunk(passages, design.settings)
    adapter = TypeAdapter(list[Passage])
    data = adapter.dump_json(corpus)
    sources = adapter.dump_json(passages)
    config = Config(**design.model_dump(), version=1, model=model.model, embedding=embedding,
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
    return config

