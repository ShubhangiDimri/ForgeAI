# ForgeAI quality report

- Stop reason Ãƒâ€š· ValueError: No valid direct evaluation cases were generated
- Selected version Ãƒâ€š· None
- Agent model Ãƒâ€š· cloudflare:@cf/meta/llama-3.3-70b-instruct-fp8-fast
- Embedding model Ãƒâ€š· sentence-transformers/all-MiniLM-L6-v2

| Version | Passed | Failed | Errors | Total | Rate | Seconds |
| --- | --- | --- | --- | --- | --- | --- |

## Assumptions and limitations

- Scores measure this frozen dataset only. The judge may share model biases with the agent.
- Exact evidence checks establish provenance. Semantic relevance and unsupported-topic decisions depend on model judgments.
- Ambiguous cases require a clarifying response, represented by the existing refusal flag.
- Errors are counted in the denominator and excluded from semantic optimization.
