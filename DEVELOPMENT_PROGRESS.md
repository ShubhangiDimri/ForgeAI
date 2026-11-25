# Development progress

## Phase 1 Prototype stabilization

- Initialized a private local Git history. Baseline commit `cc4524e` preserves the original source, tests and historical academic artifacts.
- Verified Python 3.13.5 and existing dependencies. Inspection found 2.88 GiB free of 15.34 GiB RAM and about 687 GiB free disk. Started Ollama at port 11439 with installed `gemma2:2b` and used cached MiniLM. No dependencies or models were downloaded.
- Baseline tests returned 14 passed in 3.83 seconds. Fresh historical-config smoke execution returned 3 of 3 passes and saved responses under `artifacts/phase1-smoke/`.
- Added preference-question filtering, topic preservation, pre-design coverage, bounded fallback review and source snapshots for rechunking. Added input validation, per-question error handling, tool traces and safe Open-Meteo weather. A live tool request returned temperature and wind for test coordinates.

## Phase 2 Evaluation generation

- Added bounded category batches and an independent candidate review step. Exact source anchors, source count, categories, IDs and duplicate normalization are checked before freezing the set.
- Dataset generation requires all five categories and 20 distinct cases. There is no handwritten fallback. Unit tests exercise success, invalid anchors, exclusive creation and tamper detection.

## Phase 3 Automated judge

- Added deterministic citation, expected evidence, refusal and required tool checks plus an independent structured semantic call. Records include the answer, retrieval, actual tools, expected facts, per-dimension judgment, score and explanation.
- Scripted tests cover passing, incorrect, ungrounded, missing evidence, wrong refusal, invalid citations and a judge error. Live validation is tracked separately.

## Phase 4 Critic and optimizer

- Added all four semantic failure categories, targeted patch proposals, max three patch iterations, unchanged frozen tests, rollback and best-version selection. Source snapshots drive rechunking and FAISS rebuilds.
- A scripted integration run produced baseline plus three candidate scorecards, retained the better baseline on ties, verified the frozen set and reloaded the chosen definition.

## Phase 5 Factory and report

- Full `build` is the default. Existing `--prototype-only` and chat still work. `evaluate --run` starts the evaluation workflow for a new prototype with source snapshots.
- Added per-case checkpoints, per-version artifacts, scorecards, iteration logs, prompt hashes and a final report. Unit tests confirm unattended CLI dispatch. Full live run evidence is tracked below.

## Phase 6 Demonstrations

- Kept the academic source documents and synthesis prompt intact. Added a synthetic procurement catalogue and two supplier documents, a procurement brief and the synthesis prompt.
- Started both full CLI runs with the installed model. Scripted routing tests verify real CSV and calculator handlers execute in sequence. Genuine model-driven tool execution and fully evaluated demos require saved live evidence.

## Phase 7 Verification

- Expanded the suite to 28 tests. The latest run at this checkpoint returned 28 passed in 5.87 seconds. Model expectations and embedding vectors are scripted where relevant.
- Prior live evidence and the new academic smoke rerun remain distinct from full-pipeline live results.


## Live generation debugging

- The first full academic run saved its generated agent and stopped before evaluation. Its model produced 0 of 8 valid direct cases. The incomplete quality report and run metadata are preserved under artifacts/full-academic.
- A live diagnostic reproduced the cause. Gemma wrote four relevant policy questions but returned an empty evidence-anchor array for each. The independent validation call accepted the questions, while the generator correctly rejected their missing evidence.
- Changed generation to source-assigned slots with model-generated questions and independent semantic checks. Added a synthetic academic procedures supplement and a separate synthesis prompt while preserving the original files.
- The first procurement build selected CSV lookup and calculator. Its initial evaluation was interrupted for the generator change. A separate evaluation from the identical built snapshot started in artifacts/full-procurement-slot and validated 3 of 8 direct cases in its first batch.
- The fresh academic full run is running under artifacts/full-academic-slot. The expanded regression suite returned 31 passed in 4.34 seconds. Both runs use the same installed Gemma model and MiniLM cache. CPU model response latency has been approximately 30 to 120 seconds during this session.
