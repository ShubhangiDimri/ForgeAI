# ForgeAI quality report

- Stop reason · iteration budget reached
- Selected version · 1
- Agent model · groq:openai/gpt-oss-120b
- Embedding model · sentence-transformers/all-MiniLM-L6-v2

| Version | Passed | Failed | Errors | Total | Rate | Seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 13 | 7 | 0 | 20 | 65.0% | 226.95 |
| 1 | 14 | 6 | 0 | 20 | 70.0% | 211.77 |

Measured improvement · yes

## Selected version checks

- correct · 19/20 scored cases
- grounded · 19/20 scored cases
- citations_relevant · 19/20 scored cases
- refusal_appropriate · 15/20 scored cases
- tools_correct · 20/20 scored cases

## Remaining failures and errors

- E009 · prompt defect · The answer correctly states that the policy documents do not specify a maximum insurance coverage amount for incoming loans, which is supported by the evidence that only records insurance limits but does not set a maximum. No citations were provided, so citations_relevant is false. The response is not a refusal, so refusal_appropriate is false. No tools were used, so tools_correct is true. Failed checks: refusal_appropriate.
- E011 · prompt defect · The answer correctly states that the policy does not specify a timeframe, which is supported by the cited evidence. However, one citation is irrelevant, so citations are not fully relevant. The assistant should have refused because the category is unsupported and a refusal was expected. Failed checks: citations_relevant, refusal_appropriate.
- E012 · prompt defect · The answer correctly states that the insurance limit is recorded at the time of logging the loan 30 days before arrival, as supported by the cited passage. No refusal was issued, and no tools were used. Failed checks: refusal_appropriate.
- E013 · prompt defect · The answer correctly states that both object identifiers and purpose must be provided, matching the cited policy. It does not refuse as the question is ambiguous but answerable, so refusal is inappropriate. Failed checks: refusal_appropriate.
- E014 · prompt defect · The cited passage states that the booking includes the route for all internal movements, with no weight restriction. The answer reflects this fact and is fully supported by the evidence. No tools were invoked, so tools_correct is true. Failed checks: refusal_appropriate.
- E015 · retrieval miss · Deterministic check found missing expected evidence, invalid citations or wrong refusal. Failed checks: correct, grounded.

## Targeted iterations

- Version 1 · Clarify scope and disambiguation after incorrect answers to refusal cases. Outcome improved.

## Assumptions and limitations

- policy files will be provided
- Scores measure this frozen dataset only. The judge may share model biases with the agent.
- Exact evidence checks establish provenance. Semantic relevance and unsupported-topic decisions depend on model judgments.
- Ambiguous cases require a clarifying response, represented by the existing refusal flag.
- Errors are counted in the denominator and excluded from semantic optimization.
