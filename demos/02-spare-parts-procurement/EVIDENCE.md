# Spare-parts procurement run evidence

Review the [brief, input documents, and synthesis prompt](README.md), then use the tables below to follow the recorded run. The raw artifacts are linked throughout. This page summarizes historical results without rerunning the agent or judge.

## Requirements and agent definition

| Field | Saved value |
| --- | --- |
| Scope | concise maritime spare-parts procurement assistant for buyers |
| Audience | unspecified |
| Tone | unspecified |
| Must answer | catalogue SKU lookup, unit prices, calculations of order subtotals, supplier lead times, returns, shipping rules |
| Must refuse | unrelated requests, information on live stock availability |
| Assumptions | CSV lookup and calculator are available as described |
| Unresolved | None recorded |
| Selected agent | v1, `groq:openai/gpt-oss-120b` |
| Retrieval settings | 120 words per chunk, 20 words overlap, top 4, minimum score 0.22 |
| Tools | `csv_lookup` (Needed for exact SKU and price retrieval from catalogue.csv), `calculator` (Required for arithmetic on order subtotals) |

[Raw requirements](../../backend/artifacts/groq-procurement-final/requirements.json) · [Groundability review](../../backend/artifacts/groq-procurement-final/coverage.json) · [Full agent definition and system prompt](../../backend/artifacts/groq-procurement-final/agent_config.json)

## Scorecards and optimization

| Version | Passed | Failed | Errors | Pass rate |
| --- | ---: | ---: | ---: | ---: |
| v0 | 12/20 | 7 | 1 | 60% |
| v1 (retained) | 11/20 | 9 | 0 | 55% |

- **Iteration 1.** Clarify tool choice and input provenance after tool-related failures. Changed `system_prompt`. Recorded outcome: no improvement.
- **Cases targeted by the critic.** E004, E008, E016.
- **Cases that changed outcome.** E002 (passed → failed), E004 (failed → passed), E006 (passed → failed), E013 (failed → passed), E015 (passed → failed), E017 (error → failed).

[Raw scorecards](../../backend/artifacts/groq-procurement-final/scorecards.json) · [Iteration log with the before-and-after prompt](../../backend/artifacts/groq-procurement-final/iteration_logs.json) · [Final report and remaining failures](../../backend/artifacts/groq-procurement-final/final_report.md)

## Check individual answers

These examples use actual answers and judge notes from retained v1.

### E004 · Passed

**Question.** Which part is identified by the SKU MQ-103?

**Recorded answer.** The SKU MQ-103 corresponds to the part "Coupling sleeve".

**Citations.** `catalogue.csv#r3:c1`.

**Recorded judgment.** The answer correctly identifies the part as "Coupling sleeve" and cites the exact evidence line from catalogue.csv#r3, matching the expected fact.

### E017 · Failed

**Question.** How many business days will it take to receive a standard part order if the supplier is Beacon Technical or Quay Marine?

**Recorded answer.** Quay Marine: 5 business days; Beacon Technical: 8 business days.

**Citations.** `quay_marine.txt#text:c1`, `beacon_technical.txt#text:c1`.

**Recorded judgment.** The assistant provided an answer instead of refusing, violating the expected behavior for an ambiguous question. The answer is grounded in the cited evidence, but it is not correct per the task requirements. Failed checks: correct, refusal_appropriate.

### Separate tool smoke test

The recorded trace looked up `MQ-101` with `csv_lookup` and used `calculator` to multiply 42.5 by 3. The saved answer reported 127.5 USD. This smoke test is separate from the 20-case score. [Tool trace](../../backend/artifacts/groq-procurement-final/tool_smoke.json)

## Frozen evaluation cases

For each case, compare the expected behavior below with the [v0 answers, retrieved chunks, and judgments](../../backend/artifacts/groq-procurement-final/case_results/v0.json) and [v1 answers, retrieved chunks, and judgments](../../backend/artifacts/groq-procurement-final/case_results/v1.json). The [original generated dataset](../../backend/artifacts/groq-procurement-final/eval_dataset.json) preserves the exact expected facts and tool requirements.

| Case | Category | Generated question | Expected behavior and evidence anchors | v0 | v1 |
| --- | --- | --- | --- | --- | --- |
| E001 | direct | If you place three purchase orders, what is the total lead time in business days? | Answer expected · `beacon_technical.txt#text` · tools: `calculator` | failed | failed |
| E002 | direct | What is the allowed return period for unused standard parts? | Answer expected · `beacon_technical.txt#text` | passed | failed |
| E003 | direct | Under what circumstance does Beacon Technical waive the restocking fee? | Answer expected · `beacon_technical.txt#text` | passed | passed |
| E004 | direct | Which part is identified by the SKU MQ-103? | Answer expected · `catalogue.csv#r3` | failed | passed |
| E005 | direct | Who is the supplier for the SKU BT-201? | Answer expected · `catalogue.csv#r4` | passed | passed |
| E006 | direct | What is the pack quantity for the SKU BT-202? | Answer expected · `catalogue.csv#r5` | passed | failed |
| E007 | direct | What must Beacon Technical receive before processing an international order? | Answer expected · `beacon_technical.txt#text` | passed | passed |
| E008 | direct | Please look up the record for SKU BT-202 and tell me its unit price in USD. | Answer expected · `catalogue.csv#r5` · tools: `csv_lookup` | failed | failed |
| E009 | out of scope | What is the primary method used in astronomy to measure distances to faraway galaxies? | Refusal expected | passed | passed |
| E010 | out of scope | What is the role of the circle of fifths in music theory? | Refusal expected | passed | passed |
| E011 | out of scope | What factors determine the suitability of wildlife habitats for endangered species? | Refusal expected | passed | passed |
| E012 | out of scope | What is the ideal temperature range for proofing dough in bread baking? | Refusal expected | passed | passed |
| E013 | unsupported | What is the shipping cost for delivering a standard part order to a remote island location? | Refusal expected | failed | passed |
| E014 | unsupported | How much would the total price be for ordering 7 units of SKU BT-203, including any applicable restocking fees if returned? | Refusal expected | failed | failed |
| E015 | unsupported | What is the expected delivery date if I place an order for SKU MQ-102 on a Friday, considering lead times and shipping days? | Refusal expected | passed | failed |
| E016 | ambiguous | What is the unit price for the part with SKU BT-202, assuming it is supplied by Beacon Technical or Quay Marine? | Refusal expected | failed | failed |
| E017 | ambiguous | How many business days will it take to receive a standard part order if the supplier is Beacon Technical or Quay Marine? | Refusal expected | error | failed |
| E018 | ambiguous | What is the return period for unused standard parts if the supplier is Beacon Technical or Quay Marine? | Refusal expected | failed | failed |
| E019 | multi document | What are the lead times for Beacon Technical and Quay Marine after purchase order acknowledgment? | Answer expected · `beacon_technical.txt#text`, `quay_marine.txt#text` | passed | passed |
| E020 | multi document | What is the return period for unused standard parts from Beacon Technical and the unit price in USD for SKU BT-203? | Answer expected · `beacon_technical.txt#text`, `catalogue.csv#r6` | passed | passed |
