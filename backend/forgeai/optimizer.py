"""Targeted configuration changes measured against a frozen case set."""
from collections import Counter
from .judge import Result
from .schema import Config, Settings


def proposed_patch(config: Config, results: list[Result], tried: tuple[dict, ...] = ()) -> tuple[Config, str, list[str]] | None:
    failures = Counter(result.failure for result in results if result.status == "failed" and result.failure)
    for category, _ in failures.most_common():
        candidate = config.model_copy(deep=True)
        settings = candidate.settings
        if category == "retrieval miss":
            if settings.top_k < 8 or settings.min_score > 0.08:
                candidate.settings = Settings(**(settings.model_dump() | {
                    "top_k": min(8, settings.top_k + 3), "min_score": min(settings.min_score, 0.08)}))
                reason = "Increase candidate breadth and reduce the similarity cutoff after missing evidence."
            elif settings.chunk_words < 180 and config.sources_sha256:
                words = min(180, settings.chunk_words + 48)
                candidate.settings = Settings(**(settings.model_dump() | {"chunk_words": words, "overlap": words // 5}))
                reason = "Increase chunk windows and add overlap so split facts can appear together."
            else:
                continue
        elif category == "hallucination" and not config.evidence_only:
            candidate.evidence_only = True
            reason = "Require a verified verbatim excerpt for each citation."
        elif category == "wrong refusal" and not config.verify_scope:
            candidate.verify_scope = True
            reason = "Recheck in-scope evidence before refusing."
        elif category == "prompt defect":
            defects = [r for r in results if r.failure == category]
            if any(r.execution.invalid_tool_call or r.case.expected_tools for r in defects):
                rule = (" Use an allowed tool when the question genuinely requires it. "
                        "Check every argument against its schema and use values from the request or retrieved evidence.")
                reason = "Clarify tool choice and input provenance after tool-related failures."
            elif any(r.case.behavior == "mixed_scope" for r in defects):
                rule = " Answer independently supported parts and state limits for the remaining parts."
                reason = "Target whole-question refusal or incomplete coverage in mixed-scope requests."
            elif any(r.case.history for r in defects):
                rule = " Preserve context qualifiers in follow-ups and ask only for details still missing."
                reason = "Target contextual and clarification follow-up failures."
            elif any(r.case.expected_refusal for r in defects):
                rule = (" Respect the stated scope and evidence limits. "
                        "If a material detail is ambiguous, ask for that detail before giving a factual answer.")
                reason = "Clarify scope and disambiguation after incorrect answers to refusal cases."
            else:
                rule = " Address each requested detail and preserve the source values, units and qualifiers."
                reason = "Strengthen factual completeness and precision after in-scope answer errors."
            if rule in config.system_prompt:
                continue
            candidate.system_prompt += rule
        else:
            continue
        if changes(config, candidate) not in tried:
            return candidate, reason, [r.case.id for r in results if r.failure == category]
    return None


def changes(before: Config, after: Config) -> dict:
    a, b = before.model_dump(), after.model_dump()
    return {key: {"before": value, "after": b[key]} for key, value in a.items() if value != b[key]}

