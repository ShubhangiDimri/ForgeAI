"""Generate and freeze an evidence-backed evaluation set."""
from collections import Counter
from pathlib import Path
import re
from typing import Literal

from pydantic import Field, model_validator
from .documents import digest
from .schema import Config, Model, Passage, Text, Tool

Category = Literal["direct", "out_of_scope", "unsupported", "ambiguous", "multi_document"]
TARGETS = {"direct": 8, "out_of_scope": 4, "unsupported": 3, "ambiguous": 3, "multi_document": 2}


class Anchor(Model):
    source_id: Text
    document: Text
    fact: Text


class Draft(Model):
    question: Text
    anchors: list[int] = Field(max_length=4)
    tools: list[Tool] = Field(max_length=2)


class Batch(Model):
    cases: list[Draft] = Field(max_length=6)


class Case(Model):
    id: Text
    question: Text
    category: Category
    expected_refusal: bool
    expected_facts: tuple[Anchor, ...]
    expected_tools: tuple[Tool, ...] = ()


def question_key(question: str) -> str:
    return " ".join(re.findall(r"\w+", question.casefold()))


class Dataset(Model):
    cases: tuple[Case, ...]

    @model_validator(mode="after")
    def validate_set(self):
        counts = Counter(c.category for c in self.cases)
        if any(counts[k] < count for k, count in TARGETS.items()):
            raise ValueError(f"Incomplete generated evaluation set: {dict(counts)}")
        if len({question_key(c.question) for c in self.cases}) != len(self.cases):
            raise ValueError("Duplicate evaluation question")
        if len({c.id for c in self.cases}) != len(self.cases):
            raise ValueError("Duplicate evaluation case ID")
        for case in self.cases:
            refusal = case.category not in {"direct", "multi_document"}
            if case.expected_refusal != refusal or bool(case.expected_facts) == refusal:
                raise ValueError(f"Invalid expectations for {case.id}")
            if refusal and case.expected_tools:
                raise ValueError(f"Unexpected tool expectation for {case.id}")
            if case.category == "multi_document" and len({a.document for a in case.expected_facts}) < 2:
                raise ValueError(f"Multiple documents required for {case.id}")
        return self


class Validation(Model):
    accepted: list[int] = Field(max_length=6)


def evidence_cards(sources: list[Passage]) -> list[Anchor]:
    cards = []
    for p in sources:
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", p.text):
            clean = " ".join(sentence.split())
            if clean:
                cards.append(Anchor(source_id=p.id, document=p.file, fact=clean[:350]))
    return cards


def generate(config: Config, sources: list[Passage], model) -> Dataset:
    cards = evidence_cards(sources)
    if len({a.document for a in cards}) < 2:
        raise ValueError("Multi-document evaluations require at least two source documents")
    cases = []
    seen = set()
    available = {t.name for t in config.tools}
    for category, target in TARGETS.items():
        print(f"Generating {target} {category} cases", flush=True)
        start = len(cases)
        for attempt in range(5):
            remaining = target - (len(cases) - start)
            if not remaining:
                break
            offset = attempt * 7 % len(cards)
            sample = (cards[offset:] + cards[:offset])[:14]
            if len({a.document for a in sample}) < 2:
                sample[-1] = next(a for a in cards if a.document != sample[0].document)
            numbered = dict(enumerate(sample, 1))
            context = {
                "category": category, "count": min(remaining, 4),
                "scope": config.requirements.scope,
                "topics": config.requirements.must_answer,
                "unsupported_topics": [t for t, f in config.coverage.items()
                                       if f.status == "unsupported" and not f.inconclusive],
                "tools": sorted(available),
                "source_cards": {i: [a.document, a.fact] for i, a in numbered.items()},
                "previous_questions": [c.question for c in cases],
            }
            draft = model.ask("eval_generate", context, Batch)
            candidates = []
            for item in draft.cases:
                key = question_key(item.question)
                if not key or key in seen or any(key == question_key(c.question) for c in candidates):
                    continue
                if any(i not in numbered for i in item.anchors) or set(item.tools) - available:
                    continue
                anchors = tuple(numbered[i] for i in dict.fromkeys(item.anchors))
                refusal = category not in {"direct", "multi_document"}
                if bool(anchors) == refusal or (refusal and item.tools):
                    continue
                if category == "multi_document" and len({a.document for a in anchors}) < 2:
                    continue
                candidates.append(Case(id="candidate", question=item.question, category=category,
                                       expected_refusal=refusal, expected_facts=anchors,
                                       expected_tools=tuple(dict.fromkeys(item.tools))))
            if not candidates:
                continue
            review = model.ask("eval_validate", {**context,
                "candidates": [c.model_dump() for c in candidates]}, Validation)
            for i in dict.fromkeys(review.accepted):
                if not 1 <= i <= len(candidates) or len(cases) - start == target:
                    continue
                candidate = candidates[i - 1]
                candidate.id = f"E{len(cases) + 1:03d}"
                seen.add(question_key(candidate.question))
                cases.append(candidate)
        if len(cases) - start < target:
            raise ValueError(f"Generated only {len(cases) - start} of {target} required {category} cases")
    return Dataset(cases=tuple(cases))


def freeze(dataset: Dataset, path: Path) -> str:
    data = dataset.model_dump_json(indent=2).encode("utf-8")
    with path.open("xb") as stream:
        stream.write(data)
    return digest(data)


def read_frozen(path: Path, fingerprint: str) -> Dataset:
    data = path.read_bytes()
    if digest(data) != fingerprint:
        raise ValueError("Frozen evaluation dataset changed")
    return Dataset.model_validate_json(data)

