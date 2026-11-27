# Museum collections run evidence

Review the [brief, input documents, and synthesis prompt](README.md), then use the tables below to follow the recorded run. The raw artifacts are linked throughout. This page summarizes historical results without rerunning the agent or judge.

## Requirements and agent definition

| Field | Saved value |
| --- | --- |
| Scope | Build an internal museum collections operations assistant for registrars and gallery staff to answer questions about loans, storage/display limits, movements, study access, and incident response using policy files. |
| Audience | registrars and gallery staff |
| Tone | concise professional |
| Must answer | incoming loans, storage, display limits by material, collection movements, study access, incident response, using the supplied policy files |
| Must refuse | unrelated requests, valuations, live shipment status, insurance quotes, using the supplied policy files |
| Assumptions | policy files will be provided |
| Unresolved | None recorded |
| Selected agent | v1, `groq:openai/gpt-oss-120b` |
| Retrieval settings | 60 words per chunk, 10 words overlap, top 3, minimum score 0.2 |
| Tools | None selected |

[Raw requirements](../../backend/artifacts/groq-museum-rehearsal-r2/requirements.json) · [Groundability review](../../backend/artifacts/groq-museum-rehearsal-r2/coverage.json) · [Full agent definition and system prompt](../../backend/artifacts/groq-museum-rehearsal-r2/agent_config.json)

## Scorecards and optimization

| Version | Passed | Failed | Errors | Pass rate |
| --- | ---: | ---: | ---: | ---: |
| v0 | 13/20 | 7 | 0 | 65% |
| v1 (retained) | 14/20 | 6 | 0 | 70% |

- **Iteration 1.** Clarify scope and disambiguation after incorrect answers to refusal cases. Changed `system_prompt`. Recorded outcome: improved.
- **Cases targeted by the critic.** E009, E010, E011, E012, E013, E014.
- **Cases that changed outcome.** E010 (failed → passed).

[Raw scorecards](../../backend/artifacts/groq-museum-rehearsal-r2/scorecards.json) · [Iteration log with the before-and-after prompt](../../backend/artifacts/groq-museum-rehearsal-r2/iteration_logs.json) · [Final report and remaining failures](../../backend/artifacts/groq-museum-rehearsal-r2/final_report.md)

## Check individual answers

These examples use actual answers and judge notes from retained v1.

### E001 · Passed

**Question.** What is the required advance notice and information an external researcher must provide to schedule a study appointment?

**Recorded answer.** The researcher must request the appointment at least ten working days in advance and supply their institution, the object identifiers to be studied, and the purpose of the study.

**Citations.** `access_and_incidents.txt#text:c1`.

**Recorded judgment.** The answer accurately states the ten‑working‑day advance notice and the required information (institution, object identifiers, purpose) as per the cited source. All claims are directly supported by the evidence, no extra unsupported material is included, and no tools were misused.

### E015 · Failed

**Question.** What action must be taken if a visitor discovers damage to a display, and what action is required when water is found near a collection object?

**Recorded answer.** If a visitor reports damage to a display, staff must immediately call the duty conservator and, once safe, restrict visitor access to the area until further instructions. If water is found near a collection object, staff must also call the duty conservator right away.

**Citations.** `environment.txt#text:c3`, `environment.txt#text:c2`.

**Recorded judgment.** Deterministic check found missing expected evidence, invalid citations or wrong refusal. Failed checks: correct, grounded.

## Frozen evaluation cases

For each case, compare the expected behavior below with the [v0 answers, retrieved chunks, and judgments](../../backend/artifacts/groq-museum-rehearsal-r2/case_results/v0.json) and [v1 answers, retrieved chunks, and judgments](../../backend/artifacts/groq-museum-rehearsal-r2/case_results/v1.json). The [original generated dataset](../../backend/artifacts/groq-museum-rehearsal-r2/eval_dataset.json) preserves the exact expected facts and tool requirements.

| Case | Category | Generated question | Expected behavior and evidence anchors | v0 | v1 |
| --- | --- | --- | --- | --- | --- |
| E001 | direct | What is the required advance notice and information an external researcher must provide to schedule a study appointment? | Answer expected · `access_and_incidents.txt#text` | passed | passed |
| E002 | direct | Who is required to supervise a study visit according to the policy? | Answer expected · `access_and_incidents.txt#text` | passed | passed |
| E003 | direct | Where must personal bags be placed during a study session? | Answer expected · `access_and_incidents.txt#text` | passed | passed |
| E004 | direct | Which items are permitted to be brought into the study room? | Answer expected · `access_and_incidents.txt#text` | passed | passed |
| E005 | out of scope | What is the primary method used in astronomy to measure the distance to faraway galaxies? | Refusal expected | passed | passed |
| E006 | out of scope | What is the role of the circle of fifths in music theory? | Refusal expected | passed | passed |
| E007 | out of scope | What type of ecosystem characterizes wildlife habitats in tropical rainforests? | Refusal expected | passed | passed |
| E008 | out of scope | What is the ideal temperature range for proofing bread dough during baking? | Refusal expected | passed | passed |
| E009 | unsupported | What is the maximum insurance coverage amount permitted for an incoming loan according to museum policy? | Refusal expected | failed | failed |
| E010 | unsupported | What is the specified maximum number of metal objects that may be displayed together in a single case? | Refusal expected | failed | passed |
| E011 | unsupported | How long does it typically take for a staff badge to be issued after a reset request is approved? | Refusal expected | failed | failed |
| E012 | ambiguous | For an incoming loan, should the registrar record the insurance limit before or after logging the loan 30 days prior to arrival? | Refusal expected | failed | failed |
| E013 | ambiguous | When scheduling a study appointment, does the external researcher need to provide the object identifiers or the purpose first? | Refusal expected | failed | failed |
| E014 | ambiguous | For internal object movements, must the booking include the route details when the object weighs over 20 kilograms or only when it is lighter? | Refusal expected | failed | failed |
| E015 | multi document | What action must be taken if a visitor discovers damage to a display, and what action is required when water is found near a collection object? | Answer expected · `access_and_incidents.txt#text`, `environment.txt#text` | failed | failed |
| E016 | multi document | What information must an external researcher provide when requesting a study appointment, and what details does the registrar record for an incoming loan? | Answer expected · `access_and_incidents.txt#text`, `loan_intake.txt#text` | passed | passed |
| E017 | direct | According to policy, what approval is required for personal reference photography? | Answer expected · `access_and_incidents.txt#text` | passed | passed |
| E018 | direct | What documentation is needed for publication photography under the policy? | Answer expected · `access_and_incidents.txt#text` | passed | passed |
| E019 | direct | What does the policy state about the use of flash? | Answer expected · `access_and_incidents.txt#text` | passed | passed |
| E020 | direct | What immediate steps does the policy require when a visitor discovers damage? | Answer expected · `access_and_incidents.txt#text` | passed | passed |
