# ForgeAI quality report

- Stop reason · frozen replay finished
- Selected version · 0
- Agent model · groq:openai/gpt-oss-120b
- Embedding model · sentence-transformers/all-MiniLM-L6-v2

| Version | Passed | Failed | Errors | Total | Rate | Seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 16 | 4 | 0 | 20 | 80.0% | 447.31 |

Measured improvement · no

## Selected version checks

- correct · 18/20 scored cases
- grounded · 19/20 scored cases
- citations_relevant · 19/20 scored cases
- refusal_appropriate · 18/20 scored cases
- tools_correct · 20/20 scored cases

## Remaining failures and errors

- E001 · hallucination · The answer correctly multiplies the unchanged unit price by the increased units sold, uses the calculator tool, and cites it appropriately. Failed checks: citations_relevant.
- E007 · hallucination · The answer correctly applies the 10-unit price increase to the current price of 188.04, multiplies by 10 units sold, yielding 1980.4, matching the cited evidence and tool result. Failed checks: correct, grounded.
- E017 · prompt defect · The answer correctly states 0% discount, citing the inventory record that shows discount_pct=0 for product P1022 in the web channel. All facts are supported by the cited evidence, no extra claims, and no tools were used. Failed checks: refusal_appropriate.
- E018 · prompt defect · The question is ambiguous and should have prompted a clarification request; the answer incorrectly provides a demand index. Failed checks: correct, refusal_appropriate.

## Assumptions and limitations

- assistant runs unattended
- uses only supplied documents
- does not invent missing facts
- cannot access live external systems
- Scores measure this frozen dataset only. The judge may share model biases with the agent.
- Exact evidence checks establish provenance. Semantic relevance and unsupported-topic decisions depend on model judgments.
- Ambiguous cases require a clarifying response, represented by the existing refusal flag.
- Errors are counted in the denominator and excluded from semantic optimization.
