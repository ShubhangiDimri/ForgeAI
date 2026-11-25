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
    unique = {}
    for question in questions:
        # Keep questions about requester decisions, including terse preference questions.
        if not re.search(r"\b(prefer\w*|audience|format|tone|scope|include|exclude|prioriti\w*|level of detail|style|refus\w*|intended|should the agent)\b", question, re.I):
            continue
        key = re.sub(r"\W+", " ", question.casefold()).strip()
        unique.setdefault(key, question)
    replies = {q: "" if unattended else input(q + " ").strip() for q in unique.values()}
    # Unanswered model questions and document examples are not requester decisions.
    answered = {q: a for q, a in replies.items() if a}
    result = model.ask("requirements", {"brief": brief, "user_answers": answered}, Requirements)
    # Preserve explicit topic lists, even when a small model omits individual items.
    explicit = re.findall(r"\banswer questions (?:about|on)\s+([^.!?\n]+)", brief, re.I)
    topics = [t.strip() for clause in explicit for t in re.split(r",\s*(?:and\s+)?|\s+and\s+", clause) if t.strip()]
    if topics:
        result.must_answer = list(dict.fromkeys(topics + (result.must_answer if answered else [])))
    requester_text = " ".join([brief, *answered.values()]).casefold()
    explicit_tone = re.search(r"\b(concise|formal|friendly|technical|professional|casual)\s+(?:\w+\s+){0,2}assistant\b",
                              requester_text)
    if explicit_tone:
        result.tone = explicit_tone[1]
    for field in ("audience", "tone"):
        value = getattr(result, field)
        if value.casefold() not in requester_text and value.casefold() != "unspecified":
            result.assumptions.append(f"Inferred {field}: {value}")
    result.unresolved = list(dict.fromkeys([*result.unresolved, *(q for q, a in replies.items() if not a)]))
    return result

