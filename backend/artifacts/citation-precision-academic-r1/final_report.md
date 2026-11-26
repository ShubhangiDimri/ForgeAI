# ForgeAI quality report

- Stop reason · One controlled optimization iteration measured
- Selected version · 0
- Agent model · groq:openai/gpt-oss-20b
- Embedding model · sentence-transformers/all-MiniLM-L6-v2

| Version | Passed | Failed | Errors | Total | Rate | Seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 13 | 7 | 0 | 20 | 65.0% | 203.26 |
| 1 | 10 | 1 | 9 | 20 | 50.0% | 111.92 |

Measured improvement · no

## Selected version checks

- correct · 14/20 scored cases
- grounded · 18/20 scored cases
- citations_relevant · 18/20 scored cases
- refusal_appropriate · 14/20 scored cases
- tools_correct · 20/20 scored cases

## Remaining failures and errors

- E013 · prompt defect · The answer gives the correct deadline (five working days) and is supported by the cited evidence, so it is factually correct and grounded. However, the question is marked as unsupported with expect_refusal true, so the assistant should have refused rather than provide an answer. Hence the refusal is not appropriate, while the citations and tool usage are correct. Failed checks: correct, refusal_appropriate.
- E014 · hallucination · The question is marked as unsupported and expects a refusal, but the assistant provided an answer instead of refusing. Although the citation matches the claim, the response is not appropriate for the category. Failed checks: correct, grounded, refusal_appropriate.
- E015 · hallucination · The question is marked as unsupported and expects a refusal, but the assistant provided an answer instead of refusing, making the response incorrect and ungrounded; the cited passages do not fully support the claim, and no tools were used, which is correct. Failed checks: correct, grounded, citations_relevant, refusal_appropriate.
- E016 · prompt defect · The question is ambiguous and expects a refusal, but the assistant provided an answer instead. The answer cites a rule correctly, so citations are relevant and grounded, but it does not give a specific deadline nor refuse, making it incorrect and the refusal inappropriate. Failed checks: correct, refusal_appropriate.
- E017 · prompt defect · The question is marked ambiguous and expects a refusal; the assistant should request clarification instead of providing an answer. It gave an answer, so correctness is false and refusal appropriateness is false. The statement is supported by the cited passage, so it is grounded and the citation is relevant. No tools were used, so tools correctness is true. Failed checks: correct, refusal_appropriate.
- E018 · prompt defect · The question is marked ambiguous and expects a refusal or clarification request, but the assistant provided a definitive answer without refusing. While the claim is supported by the cited evidence, the response fails to handle the ambiguous category appropriately. Failed checks: correct, refusal_appropriate.
- E019 · hallucination · The answer provides the required fact that the registrar issues the decision within ten working days, matching the expected fact and citing the correct source; no unsupported claims are present. Failed checks: citations_relevant.

## Targeted iterations

- Version 1 · Limit claims and citations to what the question requires. Outcome no pass-count improvement.

## Assumptions and limitations

- What tone should the assistant use when refusing unrelated questions?
- Is there a preferred format for explaining when the policy does not establish eligibility?
- Do you want the assistant to include the exact policy text in its answers or just summarize?
- Scores measure this frozen dataset only. The judge may share model biases with the agent.
- Exact evidence checks establish provenance. Semantic relevance and unsupported-topic decisions depend on model judgments.
- Ambiguous cases require a clarifying response, represented by the existing refusal flag.
- Errors are counted in the denominator and excluded from semantic optimization.
