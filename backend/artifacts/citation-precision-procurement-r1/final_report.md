# ForgeAI quality report

- Stop reason · One controlled optimization iteration measured
- Selected version · 0
- Agent model · groq:openai/gpt-oss-120b
- Embedding model · sentence-transformers/all-MiniLM-L6-v2

| Version | Passed | Failed | Errors | Total | Rate | Seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 14 | 6 | 0 | 20 | 70.0% | 142.31 |
| 1 | 14 | 6 | 0 | 20 | 70.0% | 239.9 |

Measured improvement · no

## Selected version checks

- correct · 17/20 scored cases
- grounded · 20/20 scored cases
- citations_relevant · 19/20 scored cases
- refusal_appropriate · 15/20 scored cases
- tools_correct · 18/20 scored cases

## Remaining failures and errors

- E001 · wrong refusal · Deterministic check found missing expected evidence, invalid citations or wrong refusal. Failed checks: correct, refusal_appropriate, tools_correct.
- E002 · hallucination · The answer correctly states Beacon Technical’s 14‑day return period for unused standard parts, but it also adds unrelated information about Quay Marine’s 30‑day period, making the citations partially irrelevant. Failed checks: citations_relevant.
- E008 · wrong refusal · Deterministic check found missing expected evidence, invalid citations or wrong refusal. Failed checks: correct, refusal_appropriate, tools_correct.
- E016 · prompt defect · The answer correctly states the unit price of $27.25 USD for SKU BT-202 supplied by Beacon Technical, supported by the cited catalogue entry. Failed checks: refusal_appropriate.
- E017 · prompt defect · The question is marked ambiguous and the instruction expects a refusal. The assistant provided a direct answer instead of refusing, violating the expected behavior. Failed checks: correct, refusal_appropriate.
- E018 · prompt defect · Answer correctly states 14 days for Beacon Technical and 30 days for Quay Marine, supported by cited evidence. No tool usage was required. Failed checks: refusal_appropriate.

## Targeted iterations

- Version 1 · Limit claims and citations to what the question requires. Outcome no pass-count improvement.

## Assumptions and limitations

- CSV lookup and calculator are available as described
- Scores measure this frozen dataset only. The judge may share model biases with the agent.
- Exact evidence checks establish provenance. Semantic relevance and unsupported-topic decisions depend on model judgments.
- Ambiguous cases require a clarifying response, represented by the existing refusal flag.
- Errors are counted in the denominator and excluded from semantic optimization.
