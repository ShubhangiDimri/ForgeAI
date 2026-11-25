"""Blinded per-case judgment with deterministic evidence checks."""
from typing import Literal
from pydantic import computed_field
from .documents import anchor_id
from .evaluation import Case
from .runner import Execution
from .schema import Model, Text

Failure = Literal["retrieval miss", "prompt defect", "hallucination", "wrong refusal"]


class Judgment(Model):
    correct: bool
    grounded: bool
    citations_relevant: bool
    refusal_appropriate: bool
    tools_correct: bool
    explanation: Text


class Result(Model):
    case: Case
    execution: Execution
    judgment: Judgment | None = None
    status: Literal["passed", "failed", "error"]
    failure: Failure | None = None
    explanation: Text

    @computed_field
    @property
    def score(self) -> int | None:
        return None if self.status == "error" else int(self.status == "passed")


def matching_facts(case: Case, chunks: dict[str, str]) -> set[int]:
    return {i for i, fact in enumerate(case.expected_facts)
            if any(anchor_id(key) == fact.source_id and fact.fact in " ".join(text.split())
                   for key, text in chunks.items())}


def classify(case: Case, execution: Execution, judgment: Judgment, evidence_gap: bool) -> Failure:
    answer = execution.answer
    assert answer is not None
    if case.expected_refusal and not answer.refused:
        return "hallucination" if not judgment.grounded else "prompt defect"
    if evidence_gap and (answer.refused or not judgment.correct or not judgment.grounded):
        return "retrieval miss"
    if not case.expected_refusal and answer.refused:
        return "wrong refusal"
    if not judgment.grounded or not judgment.citations_relevant:
        return "hallucination"
    return "prompt defect"


def assess(case: Case, execution: Execution, model) -> Result:
    base = dict(case=case, execution=execution)
    answer = execution.answer
    if execution.invalid_citation:
        return Result(**base, status="failed", failure="hallucination", explanation=execution.error or "Invalid citation")
    if execution.error or answer is None:
        return Result(**base, status="error", explanation=execution.error or "No answer was produced")
    evidence = {p.id: p.text for p in execution.retrieved}
    for call in execution.tools:
        evidence.update(call.results)
    cited = {key: evidence[key] for key in answer.citations if key in evidence}
    membership = len(cited) == len(set(answer.citations)) and (answer.refused or bool(cited))
    expected = set(range(len(case.expected_facts)))
    evidence_gap = matching_facts(case, evidence) != expected
    # All expected source documents should be represented by at least one relevant citation.
    covered_sources = {anchor_id(key) for key in cited}
    expected_documents = {a.document for a in case.expected_facts}
    cited_documents = {a.document for a in case.expected_facts if a.source_id in covered_sources}
    tool_names = {tool.name for tool in execution.tools if tool.results}
    tools_correct = set(case.expected_tools) <= tool_names and (not case.expected_refusal or not tool_names)
    if not membership or (not case.expected_refusal and answer.refused) or (evidence_gap and not case.expected_refusal):
        judgment = Judgment(correct=False, grounded=membership and not evidence_gap, citations_relevant=membership,
                            refusal_appropriate=answer.refused == case.expected_refusal, tools_correct=tools_correct,
                            explanation="Deterministic check found missing expected evidence, invalid citations or wrong refusal.")
    else:
        try:
            judgment = model.ask("judge", {
                "question": case.question, "category": case.category,
                "expect_refusal": case.expected_refusal, "expected_facts": [a.model_dump() for a in case.expected_facts],
                "expected_tools": case.expected_tools, "answer": answer.model_dump(),
                "cited_evidence": cited, "retrieved_evidence": evidence,
                "tool_trace": [tool.model_dump() for tool in execution.tools],
            }, Judgment)
        except (RuntimeError, ValueError, OSError) as exc:
            return Result(**base, status="error", explanation=f"Judge error: {exc}")
        judgment.citations_relevant &= membership and (answer.refused or expected_documents <= cited_documents)
        judgment.refusal_appropriate &= answer.refused == case.expected_refusal
        judgment.tools_correct &= tools_correct
    passed = all([judgment.correct, judgment.grounded, judgment.citations_relevant,
                  judgment.refusal_appropriate, judgment.tools_correct])
    reason = judgment.explanation
    failed_dimensions = [key for key, value in judgment.model_dump().items() if value is False]
    if failed_dimensions:
        reason += " Failed checks: " + ", ".join(failed_dimensions) + "."
    return Result(**base, judgment=judgment, status="passed" if passed else "failed",
                  failure=None if passed else classify(case, execution, judgment, evidence_gap), explanation=reason)

