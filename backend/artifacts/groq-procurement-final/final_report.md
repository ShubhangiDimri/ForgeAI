# ForgeAI quality report

- Stop reason · iteration budget reached
- Selected version · 0
- Agent model · groq:openai/gpt-oss-120b
- Embedding model · sentence-transformers/all-MiniLM-L6-v2

| Version | Passed | Failed | Errors | Total | Rate | Seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 12 | 7 | 1 | 20 | 60.0% | 349.33 |
| 1 | 11 | 9 | 0 | 20 | 55.0% | 55.56 |

Measured improvement · no

## Selected version checks

- correct · 14/17 scored cases
- grounded · 14/17 scored cases
- citations_relevant · 15/17 scored cases
- refusal_appropriate · 13/17 scored cases
- tools_correct · 15/17 scored cases

## Remaining failures and errors

- E001 · wrong refusal · Deterministic check found missing expected evidence, invalid citations or wrong refusal. Failed checks: correct, refusal_appropriate, tools_correct.
- E004 · prompt defect · Tool not permitted: csv_lookup
- E008 · prompt defect · Tool not permitted: csv_lookup
- E013 · hallucination · The assistant correctly refused to answer, as the question is unsupported and no shipping rule data for remote islands is provided. No evidence or citations were needed, and no tools were invoked. Failed checks: grounded.
- E014 · hallucination · The assistant failed to refuse as required for an unsupported category and provided incomplete information about restocking fees. Failed checks: correct, grounded, citations_relevant, refusal_appropriate, tools_correct.
- E016 · prompt defect · The answer correctly states the unit price of $27.25 USD for SKU BT-202 supplied by Beacon Technical, which matches the cited evidence. No refusal was needed, and no tools were used. Failed checks: refusal_appropriate.
- E017 · error · Judge error: Groq openai/gpt-oss-20b returned HTTP 429
- E018 · hallucination · The assistant provided an answer instead of refusing, violating the instruction to refuse for an ambiguous question. The answer is not grounded, citations are irrelevant, and no tools were used. Failed checks: correct, grounded, citations_relevant, refusal_appropriate.

## Targeted iterations

- Version 1 · Clarify tool choice and input provenance after tool-related failures. Outcome no improvement.

## Assumptions and limitations

- CSV lookup and calculator are available as described
- Scores measure this frozen dataset only. The judge may share model biases with the agent.
- Exact evidence checks establish provenance. Semantic relevance and unsupported-topic decisions depend on model judgments.
- Ambiguous cases require a clarifying response, represented by the existing refusal flag.
- Errors are counted in the denominator and excluded from semantic optimization.
