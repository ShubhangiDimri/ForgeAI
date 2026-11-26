"""Functional regressions with mocked LLM responses and provider transport."""
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from api import main
from forgeai import coverage, intake, llm, tools, workflow
from forgeai.evaluation import Case
from forgeai.judge import Judgment, Result, assess
from forgeai.runner import Runner, ChatTurn, Execution
from forgeai.schema import Answer, Passage
from tests.test_full_factory import saved_config


def test_live_requirement_survives_intake_and_has_no_static_support():
    model = Mock()
    req = saved_config().requirements.model_copy(deep=True)
    model.ask.side_effect = lambda stage, payload, schema: schema(questions=[]) if stage == "questions" else req
    brief = "Answer questions about fees and passes. Also provide real-time availability."
    seen = []

    def reply(questions):
        seen.extend(questions)
        return {questions[0]: "Disclose the gap."}

    requirements = intake.interview(brief, [], True, model, answer_questions=reply)
    assert seen and requirements.requester_answers[seen[0]] == "Disclose the gap."
    assert requirements.original_brief == brief
    assert "real-time availability" in requirements.must_answer
    index = Mock()
    findings = coverage.assess(requirements.model_copy(update={"must_answer": ["real-time availability"]}), index, model)
    assert findings["real-time availability"].status == "unsupported"
    index.search.assert_not_called()


def test_calculation_inputs_require_actual_quotes_and_exact_numbers():
    evidence = {"fees#text:c1": "Base: 42. Deposit: 5. Currency INR."}
    plan = {"operation": "sum", "unit": "INR", "components": [
        {"label": "Base", "value": 42, "source": "fees#text:c1", "quote": "Base: 42."},
        {"label": "Deposit", "value": 5, "source": "fees#text:c1", "quote": "Deposit: 5."},
    ]}
    assert tools.verified_sum(plan, evidence)[1] == "47"
    plan["components"][1]["value"] = 7
    with pytest.raises(ValueError, match="quotation"):
        tools.verified_sum(plan, evidence)


def test_grounding_off_and_fresh_chat_do_not_touch_retrieval():
    runner = Runner.__new__(Runner)
    runner.model = Mock()
    runner.index = Mock()
    off = runner.trace("What is the rule?", grounding=False)
    assert off.answer.outcome == "ungrounded"
    assert not off.retrieved and not off.answer.citations
    fresh = runner.trace("What was my previous question?")
    assert "no previous question" in fresh.answer.answer
    runner.model.ask.assert_not_called()
    runner.index.search.assert_not_called()


def test_context_rewrites_using_user_history_before_retrieval():
    agent = Runner.__new__(Runner)
    agent.model = Mock()
    agent.model.ask.side_effect = lambda stage, payload, schema: schema(question="Fee for blue permit")
    agent._answer = Mock(return_value=Answer(answer="42", citations=["policy#text:c1"], refused=False))
    agent.trace("How much is it?", history=[ChatTurn(question="What is a blue permit?")])
    payload = agent.model.ask.call_args.args[1]
    assert payload["history"][0]["question"] == "What is a blue permit?"
    assert agent._answer.call_args.args[0] == "Fee for blue permit"


def test_api_grounding_off_skips_runner_load(tmp_path, monkeypatch):
    archive = tmp_path / "example"
    archive.mkdir()
    (archive / "agent_config.json").write_text('{"model":"mock"}')
    monkeypatch.setattr(main, "ARTIFACTS_DIR", tmp_path)
    runner = Mock(side_effect=AssertionError("must not load index"))
    monkeypatch.setattr(main, "_get_runner", runner)
    response = TestClient(main.app).post("/api/runs/example/chat", json={
        "question": "What is the rule?", "grounding": False, "conversation_id": "new",
    })
    assert response.status_code == 200
    assert response.json()["conversation_id"] == "new"
    assert response.json()["retrieved"] == []
    runner.assert_not_called()


def test_long_429_cooldown_skips_a_duplicate_network_call(monkeypatch):
    request = Request("https://example.com")
    transport = Mock(side_effect=HTTPError(request.full_url, 429, "limit", {"Retry-After": "585"}, None))
    monkeypatch.setattr(llm, "urlopen", transport)
    monkeypatch.setattr(llm, "_COOLDOWNS", {})
    for _ in range(2):
        with pytest.raises(llm.ProviderError) as error:
            llm.provider_response(request, "fixture", "mock-credential", 1)
        assert error.value.status == 429 and error.value.retry_after > 580
    assert transport.call_count == 1


def test_429_recovery_preserves_frozen_dataset_and_partial_results(tmp_path, monkeypatch):
    from tests.test_full_factory import DraftModel, FIXTURES
    draft = DraftModel()
    draft.model = "mock"
    config = saved_config().model_copy(update={"model": "mock"})
    fake_runner = Mock(config=config, sources=FIXTURES, model=draft)
    fake_runner.trace.return_value = Execution()
    monkeypatch.setattr(workflow, "Runner", lambda _: fake_runner)
    monkeypatch.setattr(workflow, "make_model", lambda _: draft)
    monkeypatch.setattr(workflow, "save_version", lambda folder, runner: (
        folder.mkdir(parents=True, exist_ok=True), (folder / "agent_config.json").write_text(config.model_dump_json())
    ))
    seen = []

    def judge(case, execution, model):
        seen.append(case.id)
        if case.id == "E002" and seen.count("E002") == 1:
            return Result(case=case, execution=execution, status="error", explanation="HTTP 429. Retry after 585 seconds.")
        return Result(case=case, execution=execution, status="passed", explanation="fixture")

    monkeypatch.setattr(workflow, "assess", judge)
    with pytest.raises(RuntimeError, match="HTTP 429"):
        workflow.run(tmp_path, max_iterations=0)
    frozen = (tmp_path / "eval_dataset.json").read_bytes()
    assert len(workflow._load_results(tmp_path / "case_results/v0.json")) == 1
    resumed = workflow.resume_scoring(tmp_path)
    assert resumed[0]["passed"] == 20
    assert seen.count("E001") == 1
    assert (tmp_path / "eval_dataset.json").read_bytes() == frozen


def test_clarification_is_scored_as_a_distinct_appropriate_behavior():
    case = Case(id="E", question="How much does it cost?", category="ambiguous", expected_refusal=True, expected_facts=())
    clarify = Answer(answer="Which permit type?", citations=[], refused=False, outcome="clarification")
    judge = Mock()
    judge.ask.return_value = Judgment(correct=True, grounded=True, citations_relevant=True,
                                      refusal_appropriate=True, tools_correct=True, explanation="Focused clarification.")
    assert assess(case, Execution(answer=clarify), judge).status == "passed"
    generic = Answer(answer="I cannot answer", citations=[], refused=True, outcome="insufficient_evidence")
    assert assess(case, Execution(answer=generic), judge).status == "failed"
def test_groq_rotates_to_fourth_key_without_changing_model(monkeypatch):
    import io
    import json

    config = {"FORGE_GROQ_KEY_SLOT": "2", "GROQ_API_KEY_2": "limited", "GROQ_API_KEY_4": "alternate"}
    monkeypatch.setattr(llm, "provider_key", lambda name: config[name] if name in config else
                        (_ for _ in ()).throw(RuntimeError("not configured")))
    monkeypatch.setattr(llm, "_COOLDOWNS", {})
    seen = []

    def transport(request, timeout):
        seen.append((request.get_header("Authorization"), json.loads(request.data)["model"]))
        if seen[-1][0] == "Bearer limited":
            raise HTTPError(request.full_url, 429, "limit", {"Retry-After": "585"}, None)
        return io.BytesIO(b'{"choices":[{"message":{"content":"{}"}}]}')

    monkeypatch.setattr(llm, "urlopen", transport)
    client = llm.Groq(llm.GROQ_DEFAULT)
    assert client.complete([], Answer, 10) == "{}"
    assert client.complete([], Answer, 10) == "{}"
    assert seen == [("Bearer limited", "openai/gpt-oss-120b"), ("Bearer alternate", "openai/gpt-oss-120b"),
                    ("Bearer alternate", "openai/gpt-oss-120b")]
    assert client.credential_slots_used == {"GROQ_API_KEY_4"}


def test_four_custom_documents_are_uploaded_to_the_same_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOADS_DIR", tmp_path)
    files = [("files", (f"policy-{i}.txt", f"Policy {i}".encode(), "text/plain")) for i in range(4)]
    result = TestClient(main.app).post("/api/uploads", files=files)
    assert result.status_code == 200
    assert len(list((tmp_path / result.json()["upload_id"]).glob("*.txt"))) == 4
def test_build_retry_reuses_ingestion_intake_and_approval(tmp_path, monkeypatch):
    from forgeai import generator, runner
    from forgeai.retrieval import Index
    from tests.test_factory import Encoder, Scripted

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "policy.txt").write_text("Attendance applies to all residents.", encoding="utf-8")
    mock = Scripted()
    original = mock.ask
    counts = {}

    def ask(stage, payload, schema):
        counts[stage] = counts.get(stage, 0) + 1
        if stage == "design" and counts[stage] == 1:
            raise llm.ProviderError("fixture", 429, 585)
        return original(stage, payload, schema)

    monkeypatch.setattr(mock, "ask", ask)
    monkeypatch.setattr(generator, "Index", lambda p, s, e: Index(p, s, e, Encoder()))
    callback = Mock(side_effect=lambda requirements, findings: requirements)
    state = {}
    for attempt in range(2):
        if not attempt:
            with pytest.raises(llm.ProviderError):
                generator.build("Student policy assistant", docs, tmp_path / "out", True, mock, "mock",
                                approve=callback, checkpoint=state)
        else:
            generator.build("Student policy assistant", docs, tmp_path / "out", True, mock, "mock",
                            approve=callback, checkpoint=state)
    assert counts["requirements"] == 1 and counts["questions"] == 1 and counts["design"] == 2
    callback.assert_called_once()


def test_small_corpus_groundability_uses_one_shared_evidence_batch():
    class Client(llm.ModelClient):
        def __init__(self):
            self.calls = []
        def ask(self, stage, payload, schema):
            self.calls.append(stage)
            return schema(findings={1: {"status": "supported", "sentence_numbers": [1], "limitation": ""},
                                    2: {"status": "supported", "sentence_numbers": [2], "limitation": ""}})

    documents = [Passage(id="policy.txt#text:c1", file="policy.txt", text="Fees are listed here. Access opens at noon.")]
    index = SimpleNamespace(passages=documents, search=lambda topic: documents)
    requirements = saved_config().requirements.model_copy(update={"must_answer": ["fees", "access times"]})
    model = Client()
    result = coverage.assess(requirements, index, model)
    assert model.calls == ["coverage_batch"]
    assert result["access times"].evidence[0].id == "policy.txt#text:c1"
    assert result["access times"].evidence[0].quote == "Access opens at noon."
def test_judge_rejects_numbers_only_present_in_uncited_evidence():
    from forgeai.evaluation import Anchor

    correct = Passage(id="policy.txt#text:c1", file="policy.txt", text="Room fee is 42.")
    distractor = Passage(id="other.txt#text:c1", file="other.txt", text="Bike rental is 95.")
    case = Case(id="example", question="What is the room fee?", category="direct", expected_refusal=False,
                expected_facts=(Anchor(source_id="policy.txt#text", document="policy.txt", fact=correct.text),))
    answer = Answer(answer="95.", citations=[correct.id], refused=False)
    judge = Mock(model="private-model-name")
    judge.ask.return_value = Judgment(correct=True, grounded=True, citations_relevant=True,
                                     refusal_appropriate=True, tools_correct=True, explanation="Fixture")
    execution = Execution(answer=answer, retrieved=[distractor, correct])
    result = assess(case, execution, judge)
    assert result.status == "failed"
    assert not result.judgment.correct and not result.judgment.grounded
    payload = judge.ask.call_args.args[1]
    assert "private-model-name" not in str(payload)
    assert list(payload["retrieved_evidence"]) == sorted([correct.id, distractor.id])


def test_judge_checks_claim_support_in_actual_cited_chunk():
    from forgeai.evaluation import Anchor

    correct = Passage(id="policy.txt#text:c1", file="policy.txt", text="The library opens Monday.")
    unrelated = Passage(id="policy.txt#text:c2", file="policy.txt", text="Bring an identification card.")
    case = Case(id="example", question="When does the library open?", category="direct", expected_refusal=False,
                expected_facts=(Anchor(source_id="policy.txt#text", document="policy.txt", fact=correct.text),))
    answer = Answer(answer="It opens Monday.", citations=[unrelated.id], refused=False)
    judge = Mock()
    judge.ask.return_value = Judgment(correct=True, grounded=True, citations_relevant=True,
                                     refusal_appropriate=True, tools_correct=True, explanation="Fixture")
    result = assess(case, Execution(answer=answer, retrieved=[correct, unrelated]), judge)
    assert result.status == "failed" and not result.judgment.citations_relevant


def test_report_emits_definition_links_and_unsupported_topics(tmp_path):
    from forgeai.schema import Finding

    config = saved_config().model_copy(update={"coverage": {
        "live availability": Finding(status="unsupported", evidence=[], limitation="No live inventory API.")
    }})
    workflow.report(tmp_path, [], [], None, "unscored", [], config)
    text = (tmp_path / "final_report.md").read_text(encoding="utf-8")
    assert "(agent_config.json)" in text and "(scorecards.json)" in text
    assert "live availability (unsupported)" in text and "No live inventory API" in text


def test_resume_rejects_more_than_three_optimization_iterations(tmp_path):
    (tmp_path / "eval_dataset.json").write_text("{}")
    workflow.write_json(tmp_path / "run_metadata.json",
                        {"status": "incomplete", "max_iterations": 4, "eval_sha256": "fixture"})
    with pytest.raises(ValueError, match="Iterations must be between 0 and 3"):
        workflow.resume_scoring(tmp_path)


def test_live_source_prompt_keeps_maximum_five_intake_questions():
    model = Mock()
    model.ask.side_effect = lambda stage, payload, schema: (
        schema(questions=[f"Preference question {i}?" for i in range(5)]) if stage == "questions"
        else saved_config().requirements.model_copy(deep=True)
    )
    reply = Mock(return_value={})
    intake.interview("Provide real-time availability.", [], True, model, answer_questions=reply)
    assert len(reply.call_args.args[0]) == 5
    assert "approved live data source" in reply.call_args.args[0][-1]
