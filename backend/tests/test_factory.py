import io
import json
from unittest.mock import Mock
from urllib.error import URLError

import numpy as np
import pymupdf
import pytest
from pydantic import ValidationError
from forgeai import generator, runner, llm
from forgeai.documents import load, chunk
from forgeai.llm import Ollama
from forgeai.retrieval import Index
from forgeai.schema import Answer, Design, Finding, Questions, Requirements, Settings
from forgeai.tools import execute


def settings(**changes):
    return Settings(**(dict(chunk_words=24, overlap=3, top_k=1, min_score=.5) | changes))


def test_loader_and_provenance(tmp_path):
    (tmp_path / "a.txt").write_text(" ".join(["rule"] * 30))
    (tmp_path / "b.csv").write_text("code,name\n001,Orange")
    with pymupdf.open() as doc:
        doc.new_page().insert_text((50, 50), "Page one")
        doc.new_page().insert_text((50, 50), "Page two")
        doc.save(tmp_path / "c.pdf")
    passages, manifest = load(tmp_path)
    chunks = chunk(passages, settings())
    assert [p.id for p in chunks] == ["a.txt#text:c1", "a.txt#text:c2", "b.csv#r1:c1", "c.pdf#p1:c1", "c.pdf#p2:c1"]
    assert chunks[1].text.count("rule") == 9
    assert chunks[-1].page == 2 and chunks[2].row == 1 and len(manifest) == 3
    assert execute("csv_lookup", dict(file="b.csv", column="code", value="001"), {"csv_lookup"}, chunks) == {"b.csv#r1:c1": chunks[2].text}


@pytest.mark.parametrize("kind", ["empty", "missing", "unknown", "corrupt", "scanned"])
def test_invalid_inputs(tmp_path, kind):
    if kind == "unknown":
        (tmp_path / "x.exe").touch()
    if kind == "corrupt":
        (tmp_path / "x.pdf").write_bytes(b"broken")
    if kind == "scanned":
        with pymupdf.open() as doc:
            doc.new_page()
            doc.save(tmp_path / "x.pdf")
    with pytest.raises((ValueError, RuntimeError)):
        load(tmp_path / "absent" if kind == "missing" else tmp_path)


def test_schema_and_tools():
    with pytest.raises(ValidationError):
        settings(overlap=24)
    with pytest.raises(ValidationError):
        Answer(answer="unsupported assertion", citations=[], refused=False)
    with pytest.raises(ValidationError):
        Questions(questions=["q"] * 6)
    with pytest.raises(ValueError, match="permitted"):
        execute("current_date", {}, set(), [])
    with pytest.raises(ValidationError):
        execute("calculator", {"expression": "42"}, {"calculator"}, [])
    assert execute("calculator", dict(operation="multiply", left=3, right=4), {"calculator"}, []) == {"tool:calculator": "12.0"}


class Encoder:
    """Deterministic test double. FAISS indexing and similarity search are real."""
    def encode(self, strings):
        return np.array([[1, 0] if "attendance" in s.lower() else [0, 1] for s in strings], dtype="float32")


def test_retrieval_settings(tmp_path):
    for name, value in [("a", "attendance"), ("b", "registration")]:
        (tmp_path / f"{name}.txt").write_text(value)
    passages, _ = load(tmp_path)
    index = Index(passages, settings(), "", Encoder())
    assert [p.text for p in index.search("attendance")] == ["attendance"]
    index.settings = settings(top_k=2, min_score=0)
    assert len(index.search("attendance")) == 2
    index.settings.min_score = .5
    assert len(index.search("attendance")) == 1


def test_invalid_json_retries_and_unavailable(monkeypatch):
    fake = Mock(side_effect=lambda *a, **k: io.BytesIO(b'{"message":{"content":"oops"}}'))
    monkeypatch.setattr(llm, "urlopen", fake)
    with pytest.raises(ValueError, match="two attempts"):
        Ollama("mock").ask("questions", {}, Questions)
    assert fake.call_count == 2
    fake.side_effect = URLError("offline")
    with pytest.raises(RuntimeError, match="offline"):
        Ollama("mock").ask("questions", {}, Questions)


class Scripted:
    """Scripted responses exercise orchestration only."""
    model = "mock"
    tool_list = []
    def ask(self, stage, payload, schema):
        if stage == "resolve_question":
            return schema(question=payload["question"])
        if stage == "questions":
            return Questions(questions=["Preferred format?"])
        if stage == "requirements":
            return Requirements(scope="student policies", audience="students", tone="short",
                                must_answer=["attendance", "scholarships"], must_refuse=[], assumptions=[], unresolved=[])
        if stage == "design":
            return Design(system_prompt="Explain policies", settings=settings(), tools=self.tool_list)
        if stage == "coverage":
            if payload["topic"] == "scholarships":
                return schema(status="unsupported", sentence_numbers=[], limitation="No scholarship policy")
            number = next(iter(payload["sentences"]))
            return schema(status="supported", sentence_numbers=[number], limitation="")
        if stage == "route":
            denied = "football" in payload["question"]
            return schema(decision="refuse" if denied else "answer", reason="Scope check")
        return Answer(answer="75 percent", citations=list(payload["evidence"]), refused=False)


def test_mocked_saved_agent_and_scope(tmp_path, monkeypatch):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "policy.txt").write_text("Attendance minimum is 75 percent.")
    def index(corpus, parameters, embedding):
        return Index(corpus, parameters, embedding, Encoder())
    monkeypatch.setattr(generator, "Index", index)
    monkeypatch.setattr(runner, "Index", index)
    model = Scripted()
    monkeypatch.setattr(runner, "make_model", lambda name: model)
    out = tmp_path / "run"
    conf = generator.build("Student policies", docs, out, True, model, "mock")
    assert conf.requirements.unresolved == ["Preferred format?"]
    assert conf.coverage["scholarships"].status == "unsupported"
    assert conf.coverage["attendance"].status == "supported"
    assert conf.tools == []
    agent = runner.Runner(out / "agent_config.json")
    assert agent.answer("minimum attendance?").citations == ["policy.txt#text:c1"]
    assert agent.answer("any scholarships?").refused
    assert agent.answer("football scores?").refused
    (out / "corpus.json").write_bytes(b"[]")
    with pytest.raises(ValueError, match="match"):
        runner.Runner(out / "agent_config.json")
    model.tool_list = [dict(name="csv_lookup", reason="Invented")]
    with pytest.raises(ValueError, match="unavailable tool"):
        generator.build("Student policies", docs, tmp_path / "invalid", True, model, "mock")

