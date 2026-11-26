"""Generate and freeze an evidence-backed evaluation set."""
from collections import Counter
from collections.abc import Callable
from itertools import combinations, product, zip_longest
from pathlib import Path
import re
from typing import Literal

from pydantic import Field, model_validator
from .documents import digest
from .schema import Config, Model, Passage, Text, Tool

Category = Literal["direct", "out_of_scope", "unsupported", "ambiguous", "multi_document"]
TARGETS = {"direct": 8, "out_of_scope": 4, "unsupported": 3, "ambiguous": 3, "multi_document": 2}
DISTRACTOR_TOPICS = ("astronomy", "music theory", "wildlife habitats", "bread baking",
                     "board games", "geology", "world geography", "gardening",
                     "film history", "architecture", "ocean currents", "photography")


class Anchor(Model):
    source_id: Text
    document: Text
    fact: Text


class Batch(Model):
    questions: list[Text] = Field(min_length=1, max_length=4)


class IndexedQuestion(Model):
    question: Text
    slot: int = Field(ge=1, le=4)


class IndexedBatch(Model):
    cases: list[IndexedQuestion] = Field(min_length=1, max_length=4)


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
        if len(self.cases) < 20 or any(not counts[category] for category in TARGETS):
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


def multi_document_pairs(cards: list[Anchor], topics: list[str]) -> list[tuple[Anchor, Anchor]]:
    """Rank evidence within each source, then interleave distinct source pairs."""
    topic_words = {word for word in question_key(" ".join(topics)).split() if len(word) > 3}
    groups: dict[str, list[Anchor]] = {}
    for card in cards:
        groups.setdefault(card.document, []).append(card)

    def words(card: Anchor) -> set[str]:
        return {word for word in question_key(card.fact).split() if len(word) > 3}

    def scope_score(card: Anchor) -> int:
        return len(words(card) & topic_words)

    for document, anchors in groups.items():
        # A large table must never crowd out the body of a small policy document.
        # Keep short documents eligible, but favor substantive facts over headings.
        body = [a for a in anchors if len(question_key(a.fact).split()) >= 5]
        groups[document] = sorted(body or anchors, key=scope_score, reverse=True)[:8]

    ranked = []
    for left, right in combinations(groups.values(), 2):
        options = [(a, b) for a, b in product(left, right)
                   if question_key(a.fact) != question_key(b.fact)]
        options.sort(key=lambda pair: (
            scope_score(pair[0]) + scope_score(pair[1]),
            len(words(pair[0]) & words(pair[1])),
        ), reverse=True)
        if options:
            ranked.append(options)
    ranked.sort(key=lambda options: scope_score(options[0][0]) + scope_score(options[0][1]),
                reverse=True)
    return [pair for group in zip_longest(*ranked) for pair in group if pair is not None]


def generate(config: Config, sources: list[Passage], model,
             checkpoint: Callable[[list[dict]], None] | None = None,
             resume: tuple[Case, ...] = ()) -> Dataset:
    cards = evidence_cards(sources)
    if len({a.document for a in cards}) < 2:
        raise ValueError("Multi-document evaluations require at least two source documents")
    multi_pairs = multi_document_pairs(cards, config.requirements.must_answer)
    cases = list(resume)
    seen = {question_key(case.question) for case in cases}
    available = {t.name for t in config.tools}
    allowed_facts = {(a.source_id, a.document, a.fact) for a in cards}
    if len(seen) != len(cases) or any(
        case.id != f"E{i:03d}" or not set(case.expected_tools) <= available
        or any((a.source_id, a.document, a.fact) not in allowed_facts for a in case.expected_facts)
        for i, case in enumerate(cases, 1)
    ):
        raise ValueError("Saved evaluation drafts do not match the source corpus or tool allowlist")
    scope_terms = set(question_key(" ".join([config.requirements.scope, *config.requirements.must_answer,
                                           *(a.fact for a in cards)])).split())
    distractors = [topic for topic in DISTRACTOR_TOPICS if not set(topic.split()) & scope_terms]
    all_source_cards = [[anchor.document, anchor.fact] for anchor in cards]
    review_full_corpus = sum(len(anchor.fact) for anchor in cards) <= 8000

    def add_cases(category: str, target: int) -> int:
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
            size = min(remaining, 4)
            slots = []
            options = []
            if category == "direct":
                used = {a.fact for c in cases if c.category == category for a in c.expected_facts}
                options = [(a,) for a in sorted(sample, key=lambda a: a.fact in used)]
            if category == "multi_document":
                if not multi_pairs:
                    return len(cases) - start
                shift = attempt * 4 % len(multi_pairs)
                options = multi_pairs[shift:] + multi_pairs[:shift]
            for position in range(size):
                anchors = options[position % len(options)] if options else ()
                requested_tools = ()
                if category == "direct" and "csv_lookup" in available and position == 0:
                    rows = [a for a in cards if a.document.lower().endswith(".csv")]
                    if rows and not any("csv_lookup" in c.expected_tools for c in cases):
                        anchors = (rows[attempt % len(rows)],)
                        requested_tools = ("csv_lookup",)
                if category == "direct" and "calculator" in available and position == 1:
                    numeric = [a for a in cards if re.search(r"\b\d+(?:\.\d+)?\b", a.fact)]
                    if numeric and not any("calculator" in c.expected_tools for c in cases):
                        anchors = (numeric[attempt % len(numeric)],)
                        requested_tools = ("calculator",)
                slots.append((anchors, requested_tools))
            context = {
                "category": category, "count": size,
                "scope": config.requirements.scope,
                "topics": config.requirements.must_answer,
                "restricted_topics": config.requirements.must_refuse,
                "agent_scope_instructions": config.system_prompt,
                "unsupported_topics": [t for t, f in config.coverage.items()
                                       if f.status == "unsupported" and not f.inconclusive],
                "tools": sorted(available),
                "source_cards": [[a.document, a.fact] for a in sample] if not options else [],
                "slots": [{"slot": i, "facts": [a.fact for a in anchors], "tools": expected_tools,
                           **({"documents": [a.document for a in anchors]} if category == "multi_document" else {})}
                          for i, (anchors, expected_tools) in enumerate(slots, 1)],
                "previous_questions": [c.question for c in cases],
            }
            if category == "out_of_scope" and distractors:
                start_topic = attempt * size
                context["unrelated_topic_seeds"] = [distractors[(start_topic + index) % len(distractors)]
                                                      for index in range(size)]
            try:
                if category == "out_of_scope" and context.get("unrelated_topic_seeds"):
                    draft = model.ask("eval_outside", {"topics": context["unrelated_topic_seeds"]}, Batch)
                    questions = {i: q for i, q in enumerate(draft.questions, 1)
                                 if any(set(seed.split()) & set(question_key(q).split())
                                        for seed in context["unrelated_topic_seeds"])}
                elif category == "ambiguous":
                    draft = model.ask("eval_ambiguity", {
                        "count": size, "scope": context["scope"], "topics": context["topics"],
                        "source_cards": all_source_cards if review_full_corpus else context["source_cards"],
                        "previous_questions": context["previous_questions"],
                    }, Batch)
                    questions = dict(enumerate(draft.questions, 1))
                elif category == "unsupported":
                    # Dedicated prompt for unsupported cases; pass unsupported topics
                    # explicitly so weaker models produce domain-relevant questions.
                    draft = model.ask("eval_unsupported", {
                        "count": size, "scope": context["scope"], "topics": context["topics"],
                        "unsupported_topics": context["unsupported_topics"],
                        "source_cards": all_source_cards if review_full_corpus else context["source_cards"],
                        "previous_questions": context["previous_questions"],
                    }, Batch)
                    questions = dict(enumerate(draft.questions, 1))
                elif category == "multi_document":
                    draft = model.ask("eval_multi_document", {
                        "scope": context["scope"], "topics": context["topics"], "category": category,
                        "slots": context["slots"], "previous_questions": context["previous_questions"],
                    }, IndexedBatch)
                    questions = {item.slot: item.question for item in draft.cases if item.slot <= size}
                elif options and size > 1:
                    draft = model.ask("eval_generate", context, IndexedBatch)
                    questions = {item.slot: item.question for item in draft.cases if item.slot <= size}
                else:
                    draft = model.ask("eval_questions", context, Batch)
                    questions = dict(enumerate(draft.questions, 1))
            except ValueError as exc:
                print(f"Rejected malformed {category} batch: {exc}", flush=True)
                continue
            candidates = []
            for position, question in questions.items():
                if position > len(slots):
                    continue
                anchors, expected_tools = slots[position - 1]
                if "calculator" in expected_tools and not re.search(
                    r"\b(calculat\w*|comput\w*|multipl\w*|divide|sum|subtotal|total)\b", question, re.I,
                ):
                    continue
                if "csv_lookup" in expected_tools and not re.search(r"\b(csv|lookup|look up)\b", question, re.I):
                    continue
                key = question_key(question)
                if not key or key in seen or any(key == question_key(c.question) for c in candidates):
                    continue
                candidates.append(Case(id="candidate", question=question, category=category,
                                       expected_refusal=not bool(anchors), expected_facts=anchors,
                                       expected_tools=expected_tools))
            if not candidates:
                print(f"{category} batch {attempt + 1} had no usable questions", flush=True)
                continue
            try:
                stage = {"ambiguous": "eval_review_ambiguity", "out_of_scope": "eval_review_outside"}.get(
                    category, "eval_validate")
                review = model.ask(stage, {
                    "category": category, "scope": context["scope"], "topics": context["topics"],
                    "restricted_topics": context["restricted_topics"],
                    **({"agent_scope_instructions": config.system_prompt} if stage == "eval_validate" else {}),
                    "candidates": [c.model_dump() for c in candidates],
                    "source_cards": (all_source_cards if review_full_corpus else context["source_cards"])
                                    if category in {"unsupported", "ambiguous"} else [],
                }, Validation)
            except ValueError as exc:
                print(f"Rejected malformed {category} review: {exc}", flush=True)
                continue
            for i in dict.fromkeys(review.accepted):
                if not 1 <= i <= len(candidates) or len(cases) - start == target:
                    continue
                candidate = candidates[i - 1]
                candidate.id = f"E{len(cases) + 1:03d}"
                seen.add(question_key(candidate.question))
                cases.append(candidate)
            if checkpoint:
                checkpoint([case.model_dump(mode="json") for case in cases])
            print(f"{category} accepted {len(cases) - start}/{target} after batch {attempt + 1}", flush=True)
        return len(cases) - start

    for category, target in TARGETS.items():
        prior = sum(case.category == category for case in cases)
        if prior < target:
            accepted = prior + add_cases(category, target - prior)
            if not accepted:
                raise ValueError(f"No valid {category} evaluation cases were generated")
            if category == "multi_document" and accepted < target:
                raise ValueError(f"Only {accepted}/{target} multi-document cases passed review")
    # The non-multi-document category counts can vary, but retain both cross-source cases.
    if len(cases) < 20:
        add_cases("direct", 20 - len(cases))
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

