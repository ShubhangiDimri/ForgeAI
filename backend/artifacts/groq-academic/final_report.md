# ForgeAI quality report

- Stop reason Ãƒâ€š· Pilot stopped after two measured versions to validate a revised evaluation rubric in a fresh run.
- Selected version Ãƒâ€š· 1
- Agent model Ãƒâ€š· groq:openai/gpt-oss-120b
- Embedding model Ãƒâ€š· sentence-transformers/all-MiniLM-L6-v2

| Version | Passed | Failed | Errors | Total | Rate | Seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 8 | 12 | 0 | 20 | 40.0% | 152.74 |
| 1 | 9 | 11 | 0 | 20 | 45.0% | 163.85 |

Measured improvement Ãƒâ€š· yes

## Selected version checks

- correct Ãƒâ€š· 17/20 scored cases
- grounded Ãƒâ€š· 18/20 scored cases
- citations_relevant Ãƒâ€š· 14/20 scored cases
- refusal_appropriate Ãƒâ€š· 14/20 scored cases
- tools_correct Ãƒâ€š· 18/20 scored cases

## Remaining failures and errors

- E002 Ãƒâ€š· wrong refusal Ãƒâ€š· Deterministic check found missing expected evidence, invalid citations or wrong refusal. Failed checks: correct, refusal_appropriate.
- E008 Ãƒâ€š· prompt defect Ãƒâ€š· Answer matches expected fact, citation supports claim, no tools used. Failed checks: refusal_appropriate.
- E010 Ãƒâ€š· hallucination Ãƒâ€š· The assistant correctly refused to answer because the question was marked out-of-scope, and no evidence or citations were provided. Failed checks: grounded, citations_relevant.
- E013 Ãƒâ€š· hallucination Ãƒâ€š· The answer correctly refused to provide policy information, which is restricted. No citations or tools were needed. Failed checks: citations_relevant.
- E014 Ãƒâ€š· hallucination Ãƒâ€š· The answer correctly states that the available evidence only gives a percentage, not a day count, so it appropriately refuses to provide an answer. Failed checks: citations_relevant, tools_correct.
- E015 Ãƒâ€š· prompt defect Ãƒâ€š· The answer correctly states that no evidence exists for appealing a reassessment grade, matching the provided documents. Failed checks: refusal_appropriate.
- E016 Ãƒâ€š· hallucination Ãƒâ€š· The answer incorrectly refuses the question; attendance appeal communication is a permitted topic. No citations support the claim, and the refusal is inappropriate. Failed checks: correct, grounded, citations_relevant, refusal_appropriate, tools_correct.
- E017 Ãƒâ€š· prompt defect Ãƒâ€š· The answer correctly states the registrar issues a decision within ten working days, as cited in academic_procedures.txt, and accurately notes that the policy omits the appeal submission deadline, which is detailed in attendance.txt. Failed checks: refusal_appropriate.
- E018 Ãƒâ€š· hallucination Ãƒâ€š· The question concerns attendance appeals, which is outside the permitted topics. Refusal is appropriate and correctly justified. Failed checks: citations_relevant.
- E019 Ãƒâ€š· wrong refusal Ãƒâ€š· Deterministic check found missing expected evidence, invalid citations or wrong refusal. Failed checks: correct, refusal_appropriate.
- E020 Ãƒâ€š· hallucination Ãƒâ€š· Answer matches expected fact and cites correct source. Failed checks: citations_relevant.

## Targeted iterations

- Version 1 Ãƒâ€š· Require a verified verbatim excerpt for each citation. Outcome improved.
- Version 2 Ãƒâ€š· Clarify scope and disambiguation after incorrect answers to refusal cases. Outcome unmeasured.

## Assumptions and limitations

- Scores measure this frozen dataset only. The judge may share model biases with the agent.
- Exact evidence checks establish provenance. Semantic relevance and unsupported-topic decisions depend on model judgments.
- Ambiguous cases require a clarifying response, represented by the existing refusal flag.
- Errors are counted in the denominator and excluded from semantic optimization.
