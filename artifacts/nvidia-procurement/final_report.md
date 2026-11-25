# ForgeAI quality report

- Stop reason Ãƒâ€š· ValueError: No valid unsupported evaluation cases were generated
- Selected version Ãƒâ€š· None
- Agent model Ãƒâ€š· nvidia:nvidia/nemotron-3.5-lightning-30b-a3b
- Embedding model Ãƒâ€š· sentence-transformers/all-MiniLM-L6-v2

| Version | Passed | Failed | Errors | Total | Rate | Seconds |
| --- | --- | --- | --- | --- | --- | --- |

## Assumptions and limitations

- CSV lookup is the authoritative source for SKU data
- calculator handles all arithmetic operations
- exact CSV file path and column headers
- specific shipping rule details
- Scores measure this frozen dataset only. The judge may share model biases with the agent.
- Exact evidence checks establish provenance. Semantic relevance and unsupported-topic decisions depend on model judgments.
- Ambiguous cases require a clarifying response, represented by the existing refusal flag.
- Errors are counted in the denominator and excluded from semantic optimization.
