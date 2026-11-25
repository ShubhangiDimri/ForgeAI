# ForgeAI quality report

- Stop reason Ãƒâ€š· iteration budget reached
- Selected version Ãƒâ€š· 0
- Agent model Ãƒâ€š· groq:openai/gpt-oss-120b
- Embedding model Ãƒâ€š· sentence-transformers/all-MiniLM-L6-v2

| Version | Passed | Failed | Errors | Total | Rate | Seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 12 | 7 | 1 | 20 | 60.0% | 349.33 |
| 1 | 11 | 9 | 0 | 20 | 55.0% | 55.56 |

Measured improvement Ãƒâ€š· no

## Selected version checks

- correct Ãƒâ€š· 14/17 scored cases
- grounded Ãƒâ€š· 14/17 scored cases
- citations_relevant Ãƒâ€š· 15/17 scored cases
- refusal_appropriate Ãƒâ€š· 13/17 scored cases
- tools_correct Ãƒâ€š· 15/17 scored cases

## Remaining failures and errors

- E001 Ãƒâ€š· wrong refusal Ãƒâ€š· Deterministic check found missing expected evidence, invalid citations or wrong refusal. Failed checks: correct, refusal_appropriate, tools_correct.
- E004 Ãƒâ€š· prompt defect Ãƒâ€š· Tool not permitted: csv_lookup
- E008 Ãƒâ€š· prompt defect Ãƒâ€š· Tool not permitted: csv_lookup
- E013 Ãƒâ€š· hallucination Ãƒâ€š· The assistant correctly refused to answer, as the question is unsupported and no shipping rule data for remote islands is provided. No evidence or citations were needed, and no tools were invoked. Failed checks: grounded.
- E014 Ãƒâ€š· hallucination Ãƒâ€š· The assistant failed to refuse as required for an unsupported category and provided incomplete information about restocking fees. Failed checks: correct, grounded, citations_relevant, refusal_appropriate, tools_correct.
- E016 Ãƒâ€š· prompt defect Ãƒâ€š· The answer correctly states the unit price of $27.25 USD for SKU BT-202 supplied by Beacon Technical, which matches the cited evidence. No refusal was needed, and no tools were used. Failed checks: refusal_appropriate.
- E017 Ãƒâ€š· error Ãƒâ€š· Judge error: Groq openai/gpt-oss-20b returned HTTP 429
- E018 Ãƒâ€š· hallucination Ãƒâ€š· The assistant provided an answer instead of refusing, violating the instruction to refuse for an ambiguous question. The answer is not grounded, citations are irrelevant, and no tools were used. Failed checks: correct, grounded, citations_relevant, refusal_appropriate.

## Targeted iterations

- Version 1 Ãƒâ€š· Clarify tool choice and input provenance after tool-related failures. Outcome no improvement.

## Assumptions and limitations

- CSV lookup and calculator are available as described
- Scores measure this frozen dataset only. The judge may share model biases with the agent.
- Exact evidence checks establish provenance. Semantic relevance and unsupported-topic decisions depend on model judgments.
- Ambiguous cases require a clarifying response, represented by the existing refusal flag.
- Errors are counted in the denominator and excluded from semantic optimization.
