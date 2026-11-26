# ForgeAI failure analysis

## Evidence and comparability

Audited both saved Groq demonstrations across baseline v0 and iteration v1. Each baseline is 12 passed, 7 semantic failures and 1 error. Each v1 is 11 passed and 9 failed, with no errors. Both selected v0. The four result files contain 20 unique, exact matches to their own frozen cases by ID. The domains have different questions, source snapshots, execution traces, hashes and agent/judge arrangements. The shared E001-E020 labels are local to each run.

- Academic SHA-256 109a387d0fd0d8bee565c33363e133fe94adef64e8e39cfcd57c8a7ff0fe5ff5. Agent GPT-OSS 20B, judge GPT-OSS 120B. The v1 excerpt requirement changed only evidence_only and regressed overall.
- Procurement SHA-256 ae6401c6f4c44f3ad77a3f10cbe9bc3cddd40b3eb63c5b1ed6f5736b96e54ca5. Agent GPT-OSS 120B, judge GPT-OSS 20B. The v1 tool guidance changed only system_prompt and regressed overall.
- Evidence is under backend/artifacts/groq-academic-final/ and backend/artifacts/groq-procurement-final/. Read eval_dataset.json, case_results/v0.json and v1.json, iteration_logs.json, run_metadata.json and final_report.md together. Historical v1 scoring was resumed. Historical runs are context, not a controlled comparison for the new code.

## Academic nonpasses

| ID and version | Expected behavior | Actual behavior and evidence | Root cause and action |
| --- | --- | --- | --- |
| E001 v1 | Submission channel with supporting citation | Correct portal. Also cited attendance.txt c1, which covers timing and minimum attendance. | Prompt defect, extraneous citation. Test citation precision. |
| E004 v0, v1 | Registration through the assessment portal | Correct portal plus module fields. academic_procedures c1/c2 support relevant claims. assessment.txt c1 does not support the portal or fields. | Prompt defect, extraneous citation. Test citation precision. |
| E013 v0, v1 | Frozen label requests refusal | Correct five-working-day appeal deadline cites attendance.txt c1. Judge acknowledges the fact. | Evaluation defect. Ask about an undocumented filing fee in the corrected set. |
| E014 v0 | Refuse or clarify an unsupported deadline | No answer. Groq route rejected JSON twice although retrieval ran. | Provider or structured response error. Keep separate from answer quality. |
| E014 v1 | Refuse or clarify an unsupported deadline | Refused the JSON-repair message instead of addressing the policy question. Judge also treated wording about the registration window as a deadline. | Prompt/transport defect, with an underspecified question. Record separately. Make the corrected case ask for an undocumented closing time. |
| E015 v0, v1 | Frozen label requests refusal | Portal and required fields are supported by academic_procedures c1/c2. The added statement that the window opens after ten days is not established by assessment.txt c1. | Evaluation defect plus an unsolicited unsupported claim. Correct the case and test precision without changing the judge. |
| E016 v0, v1 | Clarify when given only Thursday | Gives the five-working-day rule, not a calendar deadline. attendance.txt c1 lacks the calendar date and applicable holidays. | Prompt defect under the exact-date interpretation. The question also allows a rule-only reading. Use a clearer ambiguous case. |
| E017 v0, v1 | Frozen label requests clarification | Correct assessment portal with academic_procedures c1. | Evaluation defect, question is determinate. Replace with an underspecified request channel. |
| E018 v0, v1 | Frozen label requests clarification | One attempt, directly supported by assessment.txt c1. | Evaluation defect, question is determinate. Ask an underspecified policy question instead. |
| E019 v0, v1 | Frozen key requires two documents | Correct ten-working-day decision time cites academic_procedures c1. The expected five-day submission limit from attendance.txt is a separate proposition the question never asks for. | Evaluation defect. Ask for both dates explicitly in the corrected set. |

## Procurement nonpasses

| ID and version | Expected behavior | Actual behavior and evidence | Root cause and action |
| --- | --- | --- | --- |
| E001 v0, v1 | Frozen key expects Beacon eight-day lead time and calculator | Asked which supplier the orders use. Both supplier lead times were retrieved. Three orders do not imply serial lead times. | Evaluation defect. Replace with an explicit calculation grounded in a catalogue row. |
| E002 v1 | State Beacon's 14-day unused-part policy | Gave the Beacon policy and volunteered Quay's distinct 30-day unopened-part policy, citing both documents. Original question omitted supplier. | Under-specified evaluation and excess answer scope. Identify the supplier in the corrected case. |
| E004 v0, E006 v1, E008 v0/v1 | Resolve the item, pack quantity or unit price. E008 explicitly requires lookup. | First CSV call returned the correct row, then historical runner attempted CSV lookup a second time and the allowlist rejected it. | Tool execution defect already fixed in the shipped runner. Existing tests and live BT-202 regression show one lookup suffices. |
| E013 v0 | Refuse remote island shipping cost | Refused without inventing charges. Judge explanation calls the refusal correct but grounded=false. | Incorrect judge decision. Preserve the current judge during measurement. |
| E014 v0, v1 | Refuse total inclusive of an unspecified return fee | Correct 103.25 USD subtotal with calculator, then states no fee information. The supplied documents do not establish a fee for this scenario. | Prompt defect under the strict refusal contract. Separate a fee-only item in the corrected set so conditional partial answers do not confound it. |
| E015 v1 | Clarify or refuse an exact delivery date | Refused on the false grounds that MQ-102 was absent. That row exists in the catalogue but was not among retrieved rows. Exact arrival still lacks required details. | Retrieval miss for SKU and hallucinated rationale. Do not claim corpus-wide absence from a retrieval subset. |
| E016 v0, v1 | Frozen label expects clarification | Gives 27.25 USD from the unique BT-202 Beacon row. There is no Quay Marine row for that SKU. | Evaluation defect. Make the item truly underspecified. |
| E017 v0 | Clarify supplier | Answer listed both lead times. Judge returned HTTP 429. | Infrastructure error. Independently, wording offered two named alternatives and invited a comparison. |
| E017 v1 | Clarify supplier | Listed Quay 5 and Beacon 8 business days. Lead time after acknowledgment is not guaranteed receipt time. | Evaluation conflates conditional comparison and ambiguity. Narrow the corrected question to an unspecified supplier and lead-time policy. |
| E018 v0, v1 | Clarify supplier | Reported both supported policies using both citations. Wording explicitly offered both suppliers. | Evaluation defect or ambiguous intent. Remove named alternatives in the corrected case. |

## Single intervention

After separating label defects and infrastructure, duplicate CSV dispatch is the strongest repeated historical runtime failure, and it is already repaired. The most repeated actionable remaining pattern is answer/citation overreach: academic E001/E004, and procurement E002 with an underspecified supplier. Retrieval returned the relevant passages. A partly relevant excerpt can still be irrelevant to the actual question, so making every citation contain a literal excerpt is insufficient.

Test a single optional answer-stage instruction requiring only requested facts and only directly supporting citations. Keep routing, tools, retrieval, and judge untouched. Keep it opt-in unless supported by a controlled result. Record the repair-message issue, false absence claims, and judge inconsistency as separate work. Use the original frozen cases for the principal comparison. Prepare corrected copies separately and establish a new baseline before interpreting a corrected-set score.

## Controlled replay

The two variants use the current runner, one fresh baseline, the original
frozen cases, the original pinned agent and judge for each domain, and the
same output budgets and judge rubric. The candidate changes only the answer
instruction. The historical cases, scores and selected definitions remain
unchanged. The corrected benchmarks are in backend/eval_datasets/corrected-v1
and have no live baseline yet.

The first academic recording had nine candidate DNS failures. It remains in
backend/artifacts/citation-precision-academic-r1. The recovery folder
citation-precision-academic-r2 preserves those errors, retained the 11
non-infrastructure candidate rows and retried the nine DNS cases with the
same models, prompts and rubric. The recovered academic result is 13/20
baseline versus 12/20 candidate, with zero infrastructure errors in either
measured arm. The experiment retained baseline. The sole pass-to-fail change
was E004. The candidate still added a window claim and cited academic_procedures
c2 for the portal even though the portal is in c1. Prompt guidance alone did
not fix this observed failure.

The first procurement attempt stopped at E005 with a judge HTTP 429 after
checkpointing four completed cases. The same pinned models resumed afterward.
NVIDIA Nemotron and the configured Cloudflare 70B model passed separate
structured-response smoke probes. The older Cloudflare 8B fallback returned
HTTP 410. Groq credential slot 1 returned 401 and slot 2 authenticated. No
provider smoke output was included in a Groq scorecard.

| Frozen replay | Fresh baseline | Citation candidate | Selected |
| --- | --- | --- | --- |
| Academic (academic-r2) | 13 passed, 7 failed, 0 errors | 12 passed, 8 failed, 0 errors | Baseline v0 |
| Procurement (procurement-r1) | 14 passed, 6 failed, 0 errors | 14 passed, 6 failed, 0 errors | Baseline v0 |

In procurement, E008 flipped to pass because the first CSV route changed from
an incorrect unit_price_usd key to the SKU key. That route runs before the
citation instruction. E014 regressed because the route went from refusing
the unsupported total to executing arithmetic and returning a partial result.
Those changes do not establish a citation benefit. Both selected artifacts
leave the option off, and it is off by default.

Reconciled all 80 completed case records with their respective source hashes
and scorecards. The same case ID, question and expectations were retained in
each pair. The only versioned configuration change was precise_citations.
All 57 backend tests passed, including three citation-option checks. The
model and HTTP mocks exercise wiring and contracts, while the scorecards
contain actual Groq results.

Next quality work should measure a fresh baseline on the corrected copies
before using them for a comparison. Consider validated lookup-key selection
and evidence-to-claim citation verification in separate experiments. Fix the
retired Cloudflare fallback model separately. The independent unseen-domain
rehearsal and deployment were not run.

## Retail rehearsal failure audit

The saved run is `backend/artifacts/retail-support-multidoc-r1/`. Both versions scored
11/20 with zero recorded provider or infrastructure errors. Version 0 remained
selected. All 40 result rows match their respective cases in the same frozen
`eval_dataset.json` (SHA-256
`67643362de90b83cb322d0feae70bd17894a2422fe089805fede7101798c0e22`).
The table covers the nine baseline nonpasses and E013, which failed only in v1.
Evidence is from `corpus.json`, `case_results/v0.json`, and `case_results/v1.json`.
Row references below refer to `inventory.csv`.

| Case and saved result | Expected and observed behavior | Root cause and supporting evidence | Targeted correction |
| --- | --- | --- | --- |
| E001, failed both | Key expects calculation from r1. Both versions asked which product. | Flawed question. No product, date, or prior observation is given. The needed r1 was absent from the traces, but retrieval cannot infer the intended product. | Identify the specific observation and keep the calculator expectation. |
| E002, failed both | Key expects r3 revenue of 5357.46. Both versions claimed there was no P1009 record. | Genuine identifier retrieval miss plus a flawed question. None of the three P1009 rows reached the agent. The question says "given date" without supplying one, and those rows have different revenues. | Supply date, region and channel. Retrieve matching rows and ask for missing qualifiers when values differ. |
| E003, failed both | Key expects stock status from r4. Both versions claimed there was no P1009 inventory. | Genuine identifier retrieval miss plus an underspecified key. Rows r2-r4 all have stockout flag 0, but inventory levels differ. No P1009 row was retrieved. | Ask for the exact observation and its two inventory fields. |
| E004, failed both | Key expects full r2 via CSV lookup. v0 refused without a call. v1 successfully looked up and cited r2-r4, but omitted some fields. | v0 missed all P1009 evidence and did not use the requested tool. In v1 the judge treated the other two matching records as unsupported even though the successful CSV call returned them. The question does not identify r2, and the answer is incomplete as a full record. | Ask for one explicit observation and all columns. Verify filtered lookup and completeness independently. |
| E007, failed both | Agent retrieved r11, cited the calculator, and answered 1,980.40. The judge explanation confirms the calculation, yet correctness and grounding are false. | Deterministic numeric check in `backend/forgeai/judge.py` requires an exact Decimal match to the saved float result 1980.3999999999999. Reproduced from both the saved numerical values and the checker. The original question also omits the observation and supposes a dollar unit despite pricing policy P4. | Identify the observation and ask for unspecified currency units. Define and test precision-aware checking for verified calculator outputs as a separate change. |
| E008, failed both | Key expects 296.17 from r15. Both versions said P1079 had no data. | Genuine identifier retrieval miss plus a flawed question. Rows r14 and r15 exist and give 177.70 and 296.17 respectively. Neither was retrieved. Pricing policy P1 limits the source to historical observations. | Specify the historical date, region and channel. Retrieve identifiers before relying on similarity. |
| E013, passed v0, failed v1 | Both appropriately refused to give a Nike shoe warranty period. v1 judge agreed that refusal was appropriate but marked the lack of a citation as incorrect and ungrounded. | Incorrect judge decision. Warranty policy W1 covers electronics only, and no other supplied document gives a shoe warranty. | Keep the question. Test consistent scoring for a bounded, supported refusal without citations. |
| E014, failed v0, passed v1 | Key expects refusal. Both versions refused, with only the CSV row in context. v0 judge's explanation endorsed the response despite a false refusal flag. | Flawed unsupported label plus a policy retrieval miss. Return policy R1 gives a general 30-calendar-day window from delivery for unused shoes with proof of purchase. The question never requires a channel-specific exception. | Replace with an undocumented exact restocking fee. Test the original question separately as a CSV-plus-policy answer. |
| E017, failed both | Key expects clarification. Both versions instead said P1022 was absent. | Genuine identifier retrieval miss and false absence claim. Rows r6/r7 both use web but have different dates, regions and discounts (30% and 0%). The original prompt focused on channel, which would not resolve the ambiguity. | Ask for the web discount while leaving date and region open. Retrieve both observations and ask which one applies. |
| E018, failed both | Key expects clarification. Both versions gave 140.85 and cited r11. | Flawed ambiguity label. P1038 has only one supplied observation, and r11 directly supports the answer. | Use an identifier with multiple matching observations and distinct demand indexes. |

The strongest repeated agent-side issue was exact CSV identifiers disappearing
from retrieval when the question matched multiple rows. In the current code,
`backend/forgeai/retrieval.py` only prioritizes a unique row and
`backend/forgeai/runner.py` otherwise falls back to similarity. The E002, E003,
E004, E008 and E017 saved traces show the consequence. Broader similarity
retrieval did not solve it. A general next change is to bring bounded exact
matches into evidence when an identifier is present, while keeping any
ambiguity about which record applies. Evaluate this independently of numeric
judge handling and benchmark repairs.

`backend/eval_datasets/corrected-v1/retail/` contains the separately versioned
20-case benchmark and provenance. Nine question texts were revised. IDs,
categories, source facts, tool expectations and refusal labels were preserved.
Pydantic validation and every expected source-anchor check passed against the
saved corpus. Establish a fresh live baseline before comparing agent changes
using the corrected benchmark. The saved 11/20 scores are historical results,
and the audit did not rescore or overwrite them.

### Exact identifier retrieval follow-up

For CSV-enabled agents, `backend/forgeai/retrieval.py` now returns all row groups
matching an explicit identifier and available qualifiers. The runner gives
each candidate one retrieval slot before adding further chunks, stays within
the configured evidence budget, and leaves a slot for separately requested
policy evidence when available. When several rows match, it tells the model
to clarify differing values and flags when the saved context is incomplete.
Short uppercase region codes no longer match lowercase prepositions.
`backend/tests/test_mixed_retrieval.py` covers repeated identifiers, exact
qualifiers, retrieval budget, and preservation of a separate policy source.
The backend suite passed 64 tests with one existing deprecation warning.

The 20 corrected retail cases were replayed through the previous runner and
the candidate in `backend/artifacts/retail-retrieval-corrected-baseline/` and
`backend/artifacts/retail-retrieval-corrected-candidate/`. Both used the same
frozen dataset, GPT-OSS 120B agent, GPT-OSS 20B judge, embeddings, judge code,
and versioned prompts. The saved runtime hashes differ only in retrieval and
runner code. The baseline had 2 passes, 1 semantic fail, and 17 HTTP 429
errors. The initial candidate attempt had 20 HTTP 401 errors on the other
configured Groq credential. Neither run is a valid answer-quality score
comparison. Their case results and infrastructure errors remain available.

The saved retrieval traces still allow a before-and-after evidence check.
For E017, baseline evidence supplied only row r7 and the candidate supplied
both r6 and r7. For E018, the candidate supplied r2, r3 and r4, where baseline
retrieved only matching row r4 alongside distractors. For E016 all three
matching rows replaced unrelated rows. In a separate live GPT-OSS 20B chat
smoke test (saved as `chat_smoke_groq_20b.json` in the candidate folder), E017
and E018 both requested clarification. E002 returned the correct number and
source row, but added a dollar symbol despite unspecified currency. The
smoke test does not contribute to either scorecard.

Keep the change in the working tree for the verified retrieval behavior.
Overall answer-quality impact requires a complete pinned comparison.

A separate pinned E018 retry on the rate-limited credential still returned
HTTP 429. The trace is preserved as `pinned_e018_retry.json` in the candidate
folder and is excluded from the original scorecards.

The same corrected retail benchmark was later completed for both versions
using the original pinned models after recovering from provider checkpoints.
Both scored 16/20. E017 and E018 now request clarification, E004 and E016
regressed, and E001/E007 remain unchanged. The complete controlled
comparison is under `backend/artifacts/retail-retrieval-key3-candidate/`.
