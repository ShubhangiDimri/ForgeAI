# ForgeAI quality report

- Stop reason · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 429. Retry after 585 seconds.
- Selected version · None
- Agent model · groq:openai/gpt-oss-120b
- Embedding model · sentence-transformers/all-MiniLM-L6-v2

| Version | Passed | Failed | Errors | Total | Rate | Seconds |
| --- | --- | --- | --- | --- | --- | --- |

## Assumptions and limitations

- assistant will use a calculator for fee calculations
- answers will include source citations
- assistant will ask for clarification when information is missing
- Scores measure this frozen dataset only. The judge may share model biases with the agent.
- Exact evidence checks establish provenance. Semantic relevance and unsupported-topic decisions depend on model judgments.
- Ambiguous cases require a clarifying response, represented by the existing refusal flag.
- Errors are counted in the denominator and excluded from semantic optimization.
