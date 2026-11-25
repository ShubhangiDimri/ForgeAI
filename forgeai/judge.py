"""Blinded per-case judgment with deterministic evidence checks."""
from decimal import Decimal
import re
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


def numeric_literals(text: str) -> set[Decimal]:
    return {Decimal(value.replace(",", "")) for value in re.findall(
        r"(?<![\w.])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?!\w)", text)}


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
    if execution.invalid_tool_call:
        return Result(**base, status="failed", failure="prompt defect", explanation=execution.error or "Invalid tool call")
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
    # Guard against a judge accepting an unrelated numeric value on simple numeric evidence.
    numeric_sources = " ".join(evidence.values())
    source_values = numeric_literals(numeric_sources)
    answer_values = numeric_literals(answer.answer)
    expected_values = numeric_literals(" ".join(fact.fact for fact in case.expected_facts))
    numeric_conflict = bool(expected_values and answer_values and not answer_values.issubset(
        source_values | numeric_literals(case.question)))
    cited_documents = {a.document for a in case.expected_facts if a.source_id in covered_sources}
    tool_names = {tool.name for tool in execution.tools if tool.results}
    tools_correct = set(case.expected_tools) <= tool_names and (not case.expected_refusal or not tool_names)
    if (case.category in {"out_of_scope", "unsupported"} and case.expected_refusal
            and answer.refused and execution.refusal_code and not answer.citations and not execution.tools):
        judgment = Judgment(correct=True, grounded=True, citations_relevant=True,
                            refusal_appropriate=True, tools_correct=True,
                            explanation=f"Agent refused without factual claims ({execution.refusal_code}).")
    elif not membership or (not case.expected_refusal and answer.refused) or (evidence_gap and not case.expected_refusal):
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
        judgment.correct &= not numeric_conflict
        judgment.grounded &= not numeric_conflict
        judgment.citations_relevant &= membership and (answer.refused or expected_documents <= cited_documents)
        if case.expected_refusal:
            judgment.refusal_appropriate &= answer.refused
            if answer.refused and not answer.citations:
                judgment.citations_relevant = True
        else:
            judgment.refusal_appropriate = not answer.refused
        if not execution.tools:
            judgment.tools_correct = tools_correct
        else:
            judgment.tools_correct &= tools_correct
    passed = all([judgment.correct, judgment.grounded, judgment.citations_relevant,
                  judgment.refusal_appropriate, judgment.tools_correct])
    reason = judgment.explanation
    failed_dimensions = [key for key, value in judgment.model_dump().items() if value is False]
    if failed_dimensions:
        reason += " Failed checks: " + ", ".join(failed_dimensions) + "."
    return Result(**base, judgment=judgment, status="passed" if passed else "failed",
                  failure=None if passed else classify(case, execution, judgment, evidence_gap), explanation=reason)

