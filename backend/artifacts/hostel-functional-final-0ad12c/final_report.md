# ForgeAI quality report

- Stop reason · RuntimeError: Provider interrupted E007: ProviderError: groq:openai/gpt-oss-20b returned HTTP 429. Retry after 2 seconds.
- Selected version · 0
- Agent model · groq:openai/gpt-oss-20b
- Embedding model · sentence-transformers/all-MiniLM-L6-v2

| Version | Passed | Failed | Errors | Total | Rate | Seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 16 | 9 | 0 | 25 | 64.0% | 168.22 |

Measured improvement · no

## Selected version checks

- correct · 17/24 scored cases
- grounded · 19/24 scored cases
- citations_relevant · 22/24 scored cases
- refusal_appropriate · 18/24 scored cases
- tools_correct · 24/24 scored cases

## Response outcomes

- Grounded · 17
- Out of scope · 5
- Partial · 1
- Tool assisted · 1

## Remaining failures and errors

- E013 · prompt defect · The question is marked as unsupported and expects a refusal, but the assistant provided a specific date instead of refusing. The provided date is supported by the cited evidence, so the claim is grounded and the citation is relevant, and no tools were used incorrectly. However, the answer is not correct for the required behavior and a refusal would have been appropriate. Failed checks: correct, refusal_appropriate.
- E014 · prompt defect · The answer correctly states that the policy does not specify a maximum duration for overnight leave, only the 24‑hour submission requirement, which is supported by the cited text. No refusal was needed and no tools were used incorrectly. Failed checks: refusal_appropriate.
- E015 · prompt defect · The question falls under an unsupported category and the expected behavior is to refuse; the assistant instead provided a detailed answer, which is incorrect behavior despite being grounded and properly cited. Failed checks: correct, refusal_appropriate.
- E016 · hallucination · The question was marked ambiguous and expected a clarification request, but the assistant gave a definitive answer instead of asking for clarification. Therefore the response is not correct or properly grounded, and the lack of a refusal/clarification makes the refusal appropriateness false. Citations match the claim, and no tools were used, so those aspects are true. Failed checks: correct, grounded, refusal_appropriate.
- E017 · hallucination · The question is marked ambiguous and expects a clarification request, but the assistant provided a definitive answer instead. Therefore the answer is not correct or properly grounded. The citation does support the claim, but the response style is wrong; a clarification request is required, not a refusal, so refusal_appropriate is false. No tools were used, so tools_correct is true. Failed checks: correct, grounded, refusal_appropriate.
- E018 · prompt defect · 4 validation errors for Arithmetic
unit
  Extra inputs are not permitted [type=extra_forbidden, input_value='INR', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/extra_forbidden
label
  Extra inputs are not permitted [type=extra_forbidden, input_value='Room fee refund', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/extra_forbidden
source
  Extra inputs are not permitted [type=extra_forbidden, input_value='hostel_fees.txt#text:c2', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/extra_forbidden
quote
  Extra inputs are not permitted [type=extra_forbidden, input_value='For cancellation before ...e room fee is refunded.', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/extra_forbidden
- E019 · hallucination · The answer misstates the refund percentage; the cited fee text refers to refunds after move‑in, not cancellations before move‑in, so the 50% claim is unsupported. The disciplinary fine of 500 INR is correctly cited, but summing the two values is irrelevant to the question. Failed checks: correct, grounded, citations_relevant.
- E020 · retrieval miss · Deterministic check found missing expected evidence, invalid citations or wrong refusal. Failed checks: correct, grounded.
- E024 · hallucination · The answer correctly states reporting a lost card and the 200 INR replacement fee, which is supported by the cited passage. However, it claims pets are not permitted without any supporting evidence, making the claim unsupported and the citation irrelevant to that part. Therefore the answer is not fully correct or grounded, citations are not fully relevant, no refusal was needed, and no tools were used as expected. Failed checks: correct, grounded, citations_relevant, refusal_appropriate.

## Targeted iterations

- Version 1 · Clarify tool choice and input provenance after tool-related failures. Outcome unmeasured.

## Assumptions and limitations

- Tone inferred as helpful/friendly from brief
- Audience inferred as hostel residents
- Inferred audience: Hostel residents
- Inferred tone: Helpful and friendly
- How to provide real‑time room availability without integration
- Which external source to cite for policy details
- Which calculator should be integrated for fee totals?
- How should the assistant cite policy documents?
- Should the assistant refuse all unrelated requests or only those outside the hostel domain?
- Scores measure this frozen dataset only. The judge may share model biases with the agent.
- Exact evidence checks establish provenance. Semantic relevance and unsupported-topic decisions depend on model judgments.
- Ambiguous cases require a clarifying response, represented by the existing refusal flag.
- Errors are counted in the denominator and excluded from semantic optimization.
