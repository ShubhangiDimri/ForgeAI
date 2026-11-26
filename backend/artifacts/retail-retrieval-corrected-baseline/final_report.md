# ForgeAI quality report

- Stop reason · iteration budget reached
- Selected version · 0
- Agent model · groq:openai/gpt-oss-120b
- Embedding model · sentence-transformers/all-MiniLM-L6-v2

| Version | Passed | Failed | Errors | Total | Rate | Seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 2 | 1 | 17 | 20 | 10.0% | 12.0 |

Measured improvement · no

## Selected version checks

- correct · 3/3 scored cases
- grounded · 3/3 scored cases
- citations_relevant · 2/3 scored cases
- refusal_appropriate · 3/3 scored cases
- tools_correct · 3/3 scored cases

## Remaining failures and errors

- E001 · hallucination · The answer correctly multiplies the unchanged unit price by the increased units sold, uses the calculator tool, and cites it appropriately. Failed checks: citations_relevant.
- E004 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 429. Retry after 177 seconds.
- E005 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 429. Retry after 369 seconds.
- E006 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 429. Retry after 212 seconds.
- E007 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 429. Retry after 233 seconds.
- E008 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 429. Retry after 259 seconds.
- E009 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 429. Retry after 218 seconds.
- E010 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 429. Retry after 216 seconds.
- E011 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 429. Retry after 253 seconds.
- E012 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 429. Retry after 210 seconds.
- E013 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 429. Retry after 442 seconds.
- E014 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 429. Retry after 257 seconds.
- E015 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 429. Retry after 430 seconds.
- E016 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 429. Retry after 441 seconds.
- E017 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 429. Retry after 254 seconds.
- E018 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 429. Retry after 253 seconds.
- E019 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 429. Retry after 463 seconds.
- E020 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 429. Retry after 455 seconds.

## Assumptions and limitations

- assistant runs unattended
- uses only supplied documents
- does not invent missing facts
- cannot access live external systems
- Scores measure this frozen dataset only. The judge may share model biases with the agent.
- Exact evidence checks establish provenance. Semantic relevance and unsupported-topic decisions depend on model judgments.
- Ambiguous cases require a clarifying response, represented by the existing refusal flag.
- Errors are counted in the denominator and excluded from semantic optimization.
