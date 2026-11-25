import json
import re
import tempfile
from pathlib import Path
from pydantic import TypeAdapter
from . import documents
from .coverage import assess
from .intake import interview
from .llm import Ollama
from .retrieval import Index
from .schema import Answer, Config, Design, Passage
from .tools import REGISTRY, select_tools


def build(brief: str, docs: Path, out: Path, unattended: bool, model: Ollama, embedding: str) -> Config:
    if out.exists() or out.resolve().is_relative_to(docs.resolve()):
        raise ValueError("Choose a new output directory outside the document folder")
    passages, manifest = documents.load(docs)
    req = interview(brief, passages, unattended, model)
    available = set(REGISTRY)
    if not any(p.cells for p in passages):
        available.remove("csv_lookup")
    design = model.ask("design", {"brief": brief, "requirements": req.model_dump(),
                       "files": list(manifest), "available_tools": sorted(available)}, Design)
    if any(t.name not in available for t in design.tools):
        raise ValueError("Model selected an unavailable tool")
    design.tools = select_tools(design.tools, " ".join([brief, *req.must_answer]))
    corpus = documents.chunk(passages, design.settings)
    index = Index(corpus, design.settings, embedding)
    coverage = assess(req, index, model)
    req.must_refuse = list(dict.fromkeys([*req.must_refuse, *(t for t, f in coverage.items() if f.status == "unsupported")]))
    data = TypeAdapter(list[Passage]).dump_json(corpus)
    config = Config(**design.model_dump(), version=1, model=model.model, embedding=embedding,
                    requirements=req, coverage=coverage, document_manifest=manifest,
                    output_contract=Answer.model_json_schema(), corpus_sha256=documents.digest(data))
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as temp:
        stage = Path(temp) / "run"
        stage.mkdir()
        for name, obj in {"requirements": req.model_dump(), "coverage": config.model_dump()["coverage"],
                          "document_manifest": manifest, "agent_config": config.model_dump()}.items():
            (stage / f"{name}.json").write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf8")
        (stage / "corpus.json").write_bytes(data)
        stage.rename(out)
    return config

