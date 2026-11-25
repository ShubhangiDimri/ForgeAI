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
        candidates = [Quote(id=p.id, quote=sentence)
                      for p in index.search(topic)
                      for sentence in re.split(r"(?<=[.!?])\s+", p.text) if sentence.strip()]
        if not candidates:
            results[topic] = Finding(status="unsupported", evidence=[], limitation="No passage cleared the retrieval cutoff.")
            continue
        numbered = {i: q.quote for i, q in enumerate(candidates, 1)}
        assessment = model.ask("coverage", {"topic": topic, "sentences": numbered}, Assessment)
        numbers = list(dict.fromkeys(assessment.sentence_numbers))
        if assessment.status == "unsupported":
            results[topic] = Finding(status="unsupported", evidence=[],
                                     limitation=assessment.limitation or "No direct answer identified.")
        elif not numbers or any(n not in numbered for n in numbers):
            results[topic] = Finding(status="unsupported", evidence=[], limitation="Invalid model evidence selection.")
        else:
            results[topic] = Finding(status=assessment.status, evidence=[candidates[n - 1] for n in numbers],
                                     limitation=assessment.limitation)
    return results

