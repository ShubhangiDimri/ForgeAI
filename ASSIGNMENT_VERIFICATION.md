# OceanAI submission verification

## Nine mandatory requirements

| # | Requirement | Evidence and status |
| --- | --- | --- |
| 1 | Intake interviewer | Verified. The question schema caps the interview at five. A regression test covers the live-source fallback at the cap. The Academic and Procurement requirements are archived, and the hostel run demonstrated interactive clarification. |
| 2 | Groundability guard | Verified. Coverage is saved before agent design. The Academic archive flags scholarship eligibility as unsupported. Procurement flags subtotal calculation as partial because quantity and operation must be supplied. Live hostel checks flagged room availability without a live inventory source. |
| 3 | Agent generator | Verified. Both saved definitions validate and include the prompt, settings, selected tools, output contract and source manifest. Academic selects zero tools. Procurement selects CSV lookup and calculator. The registry contains those tools, current date and keyless Open-Meteo weather. |
| 4 | Evaluation generator | Verified. Both saved demonstrations have 20 distinct frozen cases across direct, out-of-scope, unsupported, ambiguous and cross-document categories. Every expected literal evidence anchor matched the saved sources. Generation prompt files are tracked and match the historical generation hashes. |
| 5 | Automated judge | Hardened and regression-tested. A consistent rubric judges one anonymous answer at a time. Evidence maps have stable ordering. Deterministic checks enforce citation membership, exact expected evidence in cited chunks, numeric provenance in cited evidence, tool use and appropriate response behavior. Separate pinned agent and judge models were used in the required demos. Shared-model bias remains possible, and archived scores predate these stricter checks. |
| 6 | Critic and optimizer | Verified. Four semantic failure classifications have mock-backed coverage, separate from infrastructure errors. The optimizer patches specific fields, reruns the frozen dataset and retains the best score. Both initial and resume paths enforce the baseline plus three-iteration maximum. Existing live logs contain changes, reasons, affected IDs, and numeric before/after scores. |
| 7 | Honest reports | Verified and improved. Archived definitions, scorecards, error traces and final reports reconcile. New reports link the selected definition, scorecards and logs, show affected cases and score comparisons, and enumerate partial, unsupported or inconclusive requirements. |
| 8 | Runnable product | Verified. The generic CLI and Streamlit Playground load saved definitions. Saved Academic and Procurement chat/tool smoke artifacts and the museum chat trace are available. |
| 9 | Two full demonstrations | Verified against tracked artifacts. Museum and Procurement are the primary pair, with Academic retained as a supplementary run. The primary runs have separate briefs and document sets, source and synthesis prompts, requirements, valid definitions and version snapshots, distinct frozen datasets, per-case traces, iteration logs, scorecards and final reports. |

## Saved demonstrations

| Run | Baseline | Iteration 1 | Retained |
| --- | --- | --- | --- |
| [Academic, supplementary](backend/artifacts/groq-academic-final/final_report.md) | 12 passed, 7 failed, 1 invalid route response | 11 passed, 9 failed, 0 errors | v0 |
| [Procurement, primary](backend/artifacts/groq-procurement-final/final_report.md) | 12 passed, 7 failed, 1 judge HTTP 429 | 11 passed, 9 failed, 0 errors | v0 |
| [Museum, primary](backend/artifacts/groq-museum-rehearsal-r2/final_report.md) | 13 passed, 7 failed, 0 errors | 14 passed, 6 failed, 0 errors | v1 |

- Museum inputs are in [demo_data/museum_rehearsal](backend/demo_data/museum_rehearsal), [brief](backend/demo_data/museum_rehearsal_brief.txt) and [synthesis prompt](backend/demo_data/museum_rehearsal_synthesis_prompt.txt).
- Academic inputs are in [demo_data/academic](backend/demo_data/academic), [brief](backend/demo_data/academic_factory_brief.txt), [synthesis prompt](backend/demo_data/synthesis_prompt.txt) and [expansion prompt](backend/demo_data/academic_expansion_prompt.txt).
- Procurement inputs are in [demo_data/procurement](backend/demo_data/procurement), [brief](backend/demo_data/procurement_brief.txt) and [synthesis prompt](backend/demo_data/procurement_synthesis_prompt.txt).
- Evaluation prompts are in [forgeai/prompts](backend/forgeai/prompts). Each archived demo directory contains its own `requirements.json`, `coverage.json`, `agent_config.json`, `eval_dataset.json`, `case_results/`, `versions/`, `scorecards.json`, `iteration_logs.json` and `final_report.md`.
- Recomputed raw input, corpus and frozen dataset hashes match each archive. Each archived scorecard reconciles with 20 distinct results, and each iteration log matches its referenced scorecards. The historical judge and answer prompts have since changed. Archived runs and scores were preserved.
- The museum rehearsal used four different documents and a different brief, ran unattended, generated a fresh 20-case dataset and completed one live iteration. The later hostel check generated 25 cases and scored 16/25 at baseline. Its optimizer attempt was interrupted by a provider rate limit and is separate from the two required demonstrations.

## Verification scope and submission handoff

- Backend pytest passed **83 tests**, with one Starlette test-client deprecation warning. The new judge and reporting regressions used local fixtures and mocked model output.
- No full live reruns or additional LLM calls were made in this audit. Historical evidence supports the demo, and the newest judge checks have automated regression evidence.
- The required demo evidence, briefs, documents, and generation prompts are already tracked. Review and commit the current fix set to the private repository before submission. Keep local uploads, environment files, caches, and credentials out of that commit.
- The live demos used hosted open-weight GPT-OSS 20B and 120B, with different models for agent and judge. They verify the workflow and archived scores with those models. End-to-end quality with the bundled small local model is a separate verification item if the review requires every stage to run on a small model.
