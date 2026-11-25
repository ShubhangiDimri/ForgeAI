import re
from .schema import Passage, Questions, Requirements
from .llm import Ollama


def interview(brief: str, passages: list[Passage], unattended: bool, model: Ollama) -> Requirements:
    preview = {}
    for item in passages:
        preview.setdefault(item.file, [])
        if len(preview[item.file]) < 2:
            preview[item.file].append(item.text[:450])
    context = {"brief": brief, "document_samples": preview}
    questions = model.ask("questions", context, Questions).questions
    replies = {q: "" if unattended else input(q + " ").strip() for q in dict.fromkeys(questions)}
    # Unanswered model questions and document examples are not requester decisions.
    answered = {q: a for q, a in replies.items() if a}
    result = model.ask("requirements", {"brief": brief, "user_answers": answered}, Requirements)
    # Preserve explicit topic lists, even when a small model omits individual items.
    explicit = re.findall(r"\banswer questions (?:about|on)\s+([^.!?\n]+)", brief, re.I)
    topics = [t.strip() for clause in explicit for t in re.split(r",\s*(?:and\s+)?|\s+and\s+", clause) if t.strip()]
    if topics:
        result.must_answer = list(dict.fromkeys(topics + result.must_answer))
    requester_text = " ".join([brief, *answered.values()]).casefold()
    for field in ("audience", "tone"):
        value = getattr(result, field)
        if value.casefold() not in requester_text and value.casefold() != "unspecified":
            result.assumptions.append(f"Inferred {field}: {value}")
    result.unresolved = list(dict.fromkeys([*result.unresolved, *(q for q, a in replies.items() if not a)]))
    return result

