# ForgeAI quality report

- Stop reason Ãƒâ€š· ValueError: No valid unsupported evaluation cases were generated
- Selected version Ãƒâ€š· None
- Agent model Ãƒâ€š· nvidia:nvidia/nemotron-3.5-lightning-30b-a3b
- Embedding model Ãƒâ€š· sentence-transformers/all-MiniLM-L6-v2

| Version | Passed | Failed | Errors | Total | Rate | Seconds |
| --- | --- | --- | --- | --- | --- | --- |

## Assumptions and limitations

- All policy content is derived solely from supplied academic policy sources
- Students have access to standard institutional processes not detailed in policy documents
- Specific numerical thresholds for minimum attendance percentages
- Exact procedural steps for attendance appeals beyond policy-stated grounds
- Detailed reassessment scheduling windows and deadlines
- Specific scholarship award amounts or renewal conditions
- Is there a preferred tone or format for explaining when policy does not establish eligibility (e.g., brief refusal vs. directed to another resource)?
- Scores measure this frozen dataset only. The judge may share model biases with the agent.
- Exact evidence checks establish provenance. Semantic relevance and unsupported-topic decisions depend on model judgments.
- Ambiguous cases require a clarifying response, represented by the existing refusal flag.
- Errors are counted in the denominator and excluded from semantic optimization.
