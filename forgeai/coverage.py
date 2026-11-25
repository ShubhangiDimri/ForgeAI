import re
from typing import Literal
from pydantic import Field
from .llm import Ollama
from .schema import Finding, Model, Passage, Quote, Requirements
from .retrieval import Index


class Assessment(Model):
    status: Literal["supported", "partial", "unsupported"]
    sentence_numbers: list[int] = Field(max_length=8)
    limitation: str


def tabular_support(topic: str, passages: list[Passage]) -> Finding | None:
    """Recognize document-backed lookup and subtotal inputs using actual table cells."""
    words = set(re.findall(r"[a-z0-9]+", topic.casefold()))
    lookup = bool(words & {"lookup", "find", "search", "record", "identifier"})
    subtotal = bool(words & {"subtotal", "subtotals", "cost", "costs", "price", "prices"}) and bool(
        words & {"calculation", "calculations", "calculate", "compute", "subtotal", "subtotals"})
    if not lookup and not subtotal:
        return None
    for passage in passages:
        if not passage.cells:
            continue
        for column, value in passage.cells.items():
            keys = set(re.findall(r"[a-z0-9]+", column.casefold()))
            if lookup and words & keys and value.strip():
                return Finding(status="supported", evidence=[Quote(id=passage.id, quote=passage.text)],
                               limitation="The source table contains the requested lookup field.")
            if subtotal and keys & {"price", "cost", "amount", "rate"} and re.fullmatch(r"\d+(?:\.\d+)?", value.strip()):
                return Finding(status="partial", evidence=[Quote(id=passage.id, quote=passage.text)],
                               limitation="The source provides numeric inputs. The quantity and operation must come from the request.")
    return None


def assess(requirements: Requirements, index: Index, model: Ollama) -> dict[str, Finding]:
    results = {}
    for topic in requirements.must_answer:
        passages = getattr(index, "passages", None)
        tabular = tabular_support(topic, passages) if isinstance(passages, list) else None
        if tabular:
            results[topic] = tabular
            continue
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
                                     retrieval_miss=not any(e.id in retrieved for e in evidence),
                                     limitation=assessment.limitation)
    return results

