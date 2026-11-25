# ForgeAI quality report

- Stop reason Ãƒâ€š· iteration budget reached
- Selected version Ãƒâ€š· 0
- Agent model Ãƒâ€š· groq:openai/gpt-oss-20b
- Embedding model Ãƒâ€š· sentence-transformers/all-MiniLM-L6-v2

| Version | Passed | Failed | Errors | Total | Rate | Seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 12 | 7 | 1 | 20 | 60.0% | 277.39 |
| 1 | 11 | 9 | 0 | 20 | 55.0% | 18.25 |

Measured improvement Ãƒâ€š· no

## Selected version checks

- correct Ãƒâ€š· 14/19 scored cases
- grounded Ãƒâ€š· 16/19 scored cases
- citations_relevant Ãƒâ€š· 14/19 scored cases
- refusal_appropriate Ãƒâ€š· 14/19 scored cases
- tools_correct Ãƒâ€š· 19/19 scored cases

## Remaining failures and errors

- E004 Ãƒâ€š· hallucination Ãƒâ€š· The answer correctly states that students register for reassessment through the assessment portal and must provide module code and component, matching the expected fact. It is grounded in the cited academic_procedures.txt passage. However, one of the provided citations (assessment.txt) does not support the claim, so not all citations are relevant. No refusal was needed and no tools were used, so tool usage is correct. Failed checks: citations_relevant.
- E013 Ãƒâ€š· prompt defect Ãƒâ€š· The answer gives the correct deadline and is properly cited, but the question is marked as unsupported and expects a refusal; the assistant should have refused rather than provide an answer. Failed checks: correct, refusal_appropriate.
- E014 Ãƒâ€š· error Ãƒâ€š· ValueError: Invalid route output after two attempts: Groq rejected the request or could not produce JSON
- E015 Ãƒâ€š· hallucination Ãƒâ€š· The question is marked as unsupported and expects a refusal, but the assistant provided an answer instead of refusing. Therefore the response is incorrect, not properly grounded, and its citations are irrelevant to the required behavior. No tools were used, which matches expectations. Failed checks: correct, grounded, citations_relevant, refusal_appropriate.
- E016 Ãƒâ€š· hallucination Ãƒâ€š· The question is ambiguous and expects a clarification request or refusal; the assistant provided a definitive answer without refusing, so correctness and grounding fail, citations are irrelevant, and refusal was inappropriate, though no tools were used. Failed checks: correct, grounded, citations_relevant, refusal_appropriate.
- E017 Ãƒâ€š· prompt defect Ãƒâ€š· The question is marked ambiguous and expects a refusal or clarification request, but the assistant provided a definitive answer. While the cited evidence supports the claim about the assessment portal, the response fails to handle the ambiguity as required. Failed checks: correct, refusal_appropriate.
- E018 Ãƒâ€š· hallucination Ãƒâ€š· The question is marked ambiguous and expects a refusal, but the assistant provided a definitive answer with a citation. Therefore the response is incorrect, not properly grounded, and the citation relevance is moot. A refusal would have been appropriate, and no tools were used, so tools correctness is true. Failed checks: correct, grounded, citations_relevant, refusal_appropriate.
- E019 Ãƒâ€š· hallucination Ãƒâ€š· The answer correctly states the registrar must decide within ten working days, matching the cited passage; the citation supports the claim, no refusal was needed, and no tools were used, so all criteria are satisfied. Failed checks: citations_relevant.

## Targeted iterations

- Version 1 Ãƒâ€š· Require a verified verbatim excerpt for each citation. Outcome no improvement.

## Assumptions and limitations

- What tone should the assistant use when refusing unrelated questions?
- Is there a preferred format for explaining when the policy does not establish eligibility?
- Do you want the assistant to include the exact policy text in its answers or just summarize?
- Scores measure this frozen dataset only. The judge may share model biases with the agent.
- Exact evidence checks establish provenance. Semantic relevance and unsupported-topic decisions depend on model judgments.
- Ambiguous cases require a clarifying response, represented by the existing refusal flag.
- Errors are counted in the denominator and excluded from semantic optimization.
