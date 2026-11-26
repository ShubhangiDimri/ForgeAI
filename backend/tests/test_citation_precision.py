"""Regression checks for the isolated answer-stage citation option."""
import pytest

from forgeai import runner
from forgeai.llm import ModelClient, PROMPTS
from forgeai.schema import Passage
from tests.test_factory import Scripted


@pytest.mark.parametrize("precise, expected", [(False, "answer"), (True, "answer_precise")])
def test_citation_instruction_changes_only_answer_stage(monkeypatch, precise, expected):
    from tests.test_full_factory import saved_config

    class Retriever:
        def search(self, question):
            return [Passage(id="policy.txt#text:c1", file="policy.txt", text="Attendance is required.")]

    class Client(Scripted):
        calls = []

        def ask(self, stage, payload, schema):
            self.calls.append((stage, payload))
            if stage == "route":
                return schema(decision="answer", reason="Supported")
            return schema(answer="Attendance is required.", citations=["policy.txt#text:c1"], refused=False)

    agent = runner.Runner.__new__(runner.Runner)
    agent.config = saved_config().model_copy(update={"precise_citations": precise})
    agent.index = Retriever()
    agent.model = Client()
    result = agent.trace("Is attendance required?")
    assert result.error is None
    assert [name for name, _ in agent.model.calls] == ["route", expected]
    assert agent.model.calls[0][1]["evidence"] == agent.model.calls[1][1]["evidence"]
    assert result.answer.citations == ["policy.txt#text:c1"]


def test_precise_prompt_preserves_grounding_contract_and_output_budget():
    base = (PROMPTS / "answer.txt").read_text().rstrip()
    candidate = (PROMPTS / "answer_precise.txt").read_text()
    assert candidate.startswith(base)
    assert "Omit citations that only mention the same topic" in candidate
    assert "multiple sources when they are necessary" in candidate
    client = ModelClient()
    assert client.output_budget("answer_precise", 0) == client.output_budget("answer", 0)
