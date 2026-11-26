# ForgeAI quality report

- Stop reason · iteration budget reached
- Selected version · 0
- Agent model · groq:openai/gpt-oss-120b
- Embedding model · sentence-transformers/all-MiniLM-L6-v2

| Version | Passed | Failed | Errors | Total | Rate | Seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 11 | 9 | 0 | 20 | 55.0% | 253.99 |
| 1 | 11 | 9 | 0 | 20 | 55.0% | 309.67 |

Measured improvement · no

## Selected version checks

- correct · 13/20 scored cases
- grounded · 12/20 scored cases
- citations_relevant · 20/20 scored cases
- refusal_appropriate · 13/20 scored cases
- tools_correct · 18/20 scored cases

## Remaining failures and errors

- E001 · retrieval miss · Deterministic check found missing expected evidence, invalid citations or wrong refusal. Failed checks: correct, grounded, refusal_appropriate, tools_correct.
- E002 · retrieval miss · Deterministic check found missing expected evidence, invalid citations or wrong refusal. Failed checks: correct, grounded, refusal_appropriate.
- E003 · retrieval miss · Deterministic check found missing expected evidence, invalid citations or wrong refusal. Failed checks: correct, grounded, refusal_appropriate.
- E004 · retrieval miss · Deterministic check found missing expected evidence, invalid citations or wrong refusal. Failed checks: correct, grounded, refusal_appropriate, tools_correct.
- E007 · hallucination · The answer correctly calculates the new revenue by adding $10 to the current price of $188.04, yielding $198.04 per unit, and multiplying by 10 units to get $1,980.40. The cited evidence provides the original price and units sold, and the calculator tool confirms the multiplication. Failed checks: correct, grounded.
- E008 · retrieval miss · Deterministic check found missing expected evidence, invalid citations or wrong refusal. Failed checks: correct, grounded, refusal_appropriate.
- E014 · prompt defect · The answer correctly states that there is insufficient information to determine the return policy timeframe, which is accurate given the provided evidence contains no policy details. Failed checks: refusal_appropriate.
- E017 · hallucination · The answer correctly refuses to provide a discount percentage because no inventory data for product P1022 is available. No citations are needed, and the refusal is appropriate for an ambiguous question with no data. Failed checks: grounded.
- E018 · hallucination · The question is marked ambiguous and expects a refusal. The assistant provided an answer instead of refusing, so it is incorrect and not appropriately refusing. Failed checks: correct, grounded, refusal_appropriate.

## Targeted iterations

- Version 1 · Increase candidate breadth and reduce the similarity cutoff after missing evidence. Outcome no improvement.

## Assumptions and limitations

- assistant runs unattended
- uses only supplied documents
- does not invent missing facts
- cannot access live external systems
- Scores measure this frozen dataset only. The judge may share model biases with the agent.
- Exact evidence checks establish provenance. Semantic relevance and unsupported-topic decisions depend on model judgments.
- Ambiguous cases require a clarifying response, represented by the existing refusal flag.
- Errors are counted in the denominator and excluded from semantic optimization.
