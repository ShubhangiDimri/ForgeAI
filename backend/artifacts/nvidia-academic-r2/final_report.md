# ForgeAI quality report

- Stop reason Ãƒâ€š· ValueError: No valid unsupported evaluation cases were generated
- Selected version Ãƒâ€š· None
- Agent model Ãƒâ€š· nvidia:nvidia/nemotron-3.5-lightning-30b-a3b
- Embedding model Ãƒâ€š· sentence-transformers/all-MiniLM-L6-v2

| Version | Passed | Failed | Errors | Total | Rate | Seconds |
| --- | --- | --- | --- | --- | --- | --- |

## Assumptions and limitations

- All policy information is derived solely from supplied academic policy sources
- Students have access to standard institutional procedures for appeals and registration
- Specific numerical thresholds for minimum attendance percentages
- Exact timelines for attendance appeals submission
- Detailed reassessment scheduling windows and deadlines
- Specific scholarship eligibility requirements and award amounts
- Should the assistant refuse questions about non-academic topics such as campus events or housing?
- Is there a desired response format for when policy does not establish eligibility, or should a standard refusal message be used?
- Scores measure this frozen dataset only. The judge may share model biases with the agent.
- Exact evidence checks establish provenance. Semantic relevance and unsupported-topic decisions depend on model judgments.
- Ambiguous cases require a clarifying response, represented by the existing refusal flag.
- Errors are counted in the denominator and excluded from semantic optimization.
