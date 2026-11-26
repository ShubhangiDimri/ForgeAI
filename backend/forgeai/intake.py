import re
from collections.abc import Callable
from .schema import Passage, Questions, Requirements
from .llm import ModelClient


def interview(brief: str, passages: list[Passage], unattended: bool, model: ModelClient, *,
              answer_questions: Callable[[list[str]], dict[str, str]] | None = None) -> Requirements:
    preview = {}
    for item in passages:
        preview.setdefault(item.file, [])
        if len(preview[item.file]) < 2:
            preview[item.file].append(item.text[:450])
    context = {"brief": brief, "document_samples": preview}
    questions = model.ask("questions", context, Questions).questions
    if re.search(r"\b(?:[a-z]+-friendly|formal tone|conversational tone|plain language)\b", brief, re.I):
        questions = [q for q in questions if not re.search(r"\b(?:tone|casual or formal)\b", q, re.I)]
    if re.search(r"\b(?:ask|request)\b.{0,32}\b(?:details|clarification)\b", brief, re.I):
        questions = [q for q in questions if not re.search(r"\b(?:asking for|request additional details|ask for missing details)\b", q, re.I)]
    if re.search(r"\b(?:calculator|calculate|totals)\b", brief, re.I):
        questions = [q for q in questions if not re.search(r"\bwhich calculator\b", q, re.I)
                     and not (re.search(r"\bcalculate\b", q, re.I) and re.search(r"\d+%", q))]
    if re.search(r"\b(?:cite|citations?)\b", brief, re.I):
        questions = [q for q in questions if not re.search(r"\b(?:how should .{0,40}cite|should .{0,40}include citations)\b", q, re.I)]
    if re.search(r"\brefuse unrelated\b", brief, re.I):
        questions = [q for q in questions if not re.search(r"\brefuse\b.{0,50}\bunrelated\b", q, re.I)]
    live_requests = re.findall(r"\b(?:real[ -]?time|live|up[ -]to[ -]date)\s+[^.;!?\n,]{2,100}", brief, re.I)
    if live_requests and not re.search(r"\b(?:API|integration|feed|if unavailable|if unsupported)\b", brief, re.I) and not any(
        re.search(r"\b(?:live|real.time|API|integration)\b", question, re.I) for question in questions
    ):
        questions = [*questions[:4], "Can you connect an approved live data source, or should the agent disclose that live information is unavailable?"]
    unique = {}
    for question in questions:
        key = re.sub(r"\W+", " ", question.casefold()).strip()
        unique.setdefault(key, question)
    replies = dict.fromkeys(unique.values(), "")
    if answer_questions and replies:
        submitted = answer_questions(list(replies))
        replies = {question: submitted.get(question, "").strip() for question in replies}
    elif not unattended:
        replies = {question: input(question + " ").strip() for question in replies}
    # Unanswered model questions and document examples are not requester decisions.
    answered = {q: a for q, a in replies.items() if a}
    result = model.ask("requirements", {"brief": brief, "user_answers": answered}, Requirements)
    # Preserve explicit topic lists, even when a small model omits individual items.
    explicit = re.findall(r"\banswer questions (?:about|on)\s+([^.!?\n]+)", brief, re.I)
    topics = [t.strip() for clause in explicit for t in re.split(r",\s*(?:and\s+)?|\s+and\s+", clause) if t.strip()]
    for topic in live_requests:
        if not re.search(r"\b(?:refuse|exclude|avoid|cannot|never|no|not)\b", brief[max(0, brief.find(topic) - 30):brief.find(topic)], re.I):
            topics.append(topic.strip())
    def topic_key(text: str) -> str:
        return " ".join(re.findall(r"\w+", text.casefold()))

    interview_questions = {topic_key(q) for q in replies}
    deduplicated = {}
    for topic in [*topics, *result.must_answer]:
        key = topic_key(topic)
        if key not in interview_questions or topic in brief:
            deduplicated.setdefault(key, topic)
    if deduplicated:
        result.must_answer = list(deduplicated.values())
    result.original_brief = brief
    result.requester_answers = answered
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

