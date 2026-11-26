# ForgeAI quality report

- Stop reason · all cases encountered execution or judge errors
- Selected version · 0
- Agent model · groq:openai/gpt-oss-120b
- Embedding model · sentence-transformers/all-MiniLM-L6-v2

| Version | Passed | Failed | Errors | Total | Rate | Seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 0 | 0 | 20 | 20 | 0.0% | 6.16 |

Measured improvement · no

## Selected version checks


## Remaining failures and errors

- E001 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 401
- E002 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 401
- E003 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 401
- E004 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 401
- E005 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 401
- E006 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 401
- E007 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 401
- E008 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 401
- E009 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 401
- E010 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 401
- E011 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 401
- E012 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 401
- E013 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 401
- E014 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 401
- E015 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 401
- E016 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 401
- E017 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 401
- E018 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 401
- E019 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 401
- E020 · error · RuntimeError: Groq openai/gpt-oss-120b returned HTTP 401

## Assumptions and limitations

- assistant runs unattended
- uses only supplied documents
- does not invent missing facts
- cannot access live external systems
- Scores measure this frozen dataset only. The judge may share model biases with the agent.
- Exact evidence checks establish provenance. Semantic relevance and unsupported-topic decisions depend on model judgments.
- Ambiguous cases require a clarifying response, represented by the existing refusal flag.
- Errors are counted in the denominator and excluded from semantic optimization.
