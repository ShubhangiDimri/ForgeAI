import re
from typing import Literal
from pydantic import Field
from .llm import Ollama
from .schema import Finding, Model, Quote, Requirements
from .retrieval import Index


class Assessment(Model):
    status: Literal["supported", "partial", "unsupported"]
    sentence_numbers: list[int] = Field(max_length=8)
    limitation: str


def assess(requirements: Requirements, index: Index, model: Ollama) -> dict[str, Finding]:
    results = {}
    for topic in requirements.must_answer:
        hits = index.search(topic)
        if hasattr(index, "passages") and isinstance(index.passages, list):
            # For small collections, inspect the entire corpus when it fits the evidence budget.
            fallback = list({p.id: p for p in [*hits, *index.passages]}.values())
            inspected = fallback if sum(len(p.text) for p in fallback) <= 5400 else hits
            exhaustive = len(inspected) == len(index.passages)
        else:
            inspected, exhaustive = hits, False
        retrieved = {p.id for p in hits}
        candidates = [Quote(id=p.id, quote=sentence)
                      for p in inspected
                      for sentence in re.split(r"(?<=[.!?])\s+", p.text) if sentence.strip()]
        if not candidates:
            results[topic] = Finding(status="unsupported", evidence=[], retrieval_miss=True, inconclusive=True,
                                     limitation="No candidate cleared retrieval and an exhaustive review did not fit.")
            continue
        numbered = {i: q.quote for i, q in enumerate(candidates, 1)}
        assessment = model.ask("coverage", {"topic": topic, "sentences": numbered}, Assessment)
        numbers = list(dict.fromkeys(assessment.sentence_numbers))
        if assessment.status == "unsupported":
            results[topic] = Finding(status="unsupported", evidence=[],
                                     inconclusive=not exhaustive,
                                     limitation=assessment.limitation or "No direct answer identified.")
        elif not numbers or any(n not in numbered for n in numbers):
            results[topic] = Finding(status="unsupported", evidence=[], inconclusive=True, limitation="Invalid model evidence selection.")
        else:
            evidence = [candidates[n - 1] for n in numbers]
            results[topic] = Finding(status=assessment.status, evidence=evidence,
                                     retrieval_miss=any(e.id not in retrieved for e in evidence),
                                     limitation=assessment.limitation)
    return results

