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

## Procurement tool execution checkpoint

- The first live tool trace called the calculator with 3 and 42.5. The calculator returned 127.5, but the model skipped the requested CSV lookup, stated 382.50 and used an invalid citation. The runner rejected the response. See artifacts/full-procurement/tool_smoke.json.
- The patch preserves scope checks, adds exact lookup for a uniquely identified row when explicitly requested and uses the calculator's actual numeric result for an explicit single calculation. The live retest executed both tools and answered 127.5 USD with catalogue.csv#r1:c1 and tool:calculator. See artifacts/full-procurement/tool_smoke_after_fix.json.
- Added deterministic coverage for lookup fields and arithmetic inputs confirmed by actual CSV cells. The corresponding tests distinguish data-supported arithmetic from an unsupported lookup field.
- Latest regression suite at this checkpoint returned 33 passed in 6.73 seconds. The live tool smoke is separate from full factory evaluation.

## Evaluation and model comparison checkpoint

- The slot-based academic retry validated eight direct and two out-of-scope cases before it was interrupted to free CPU. The original slot-based procurement retry validated eight direct cases and stopped after generating only two of its four preferred out-of-scope cases.
- The revised generator requires twenty distinct questions across all five categories, with adaptive category counts. It saves accepted cases as progress before freezing any full set. Source-excluded topic seeds are used to improve out-of-scope drafting.
- A live Gemma diagnostic produced an in-scope supplier lead-time question in the out-of-scope category and its same-model reviewer approved it. A separate seeded diagnostic produced four unrelated questions. The latter is a generation diagnostic, not a measured evaluation.
- The latest Gemma procurement run saved three candidate cases before being interrupted for model comparison. Audit found an invalid calculator expectation among them. Deterministic checks now reject calculator and lookup cases without explicit corresponding intent.
- The regression command returned 35 passed in 4.24 seconds under Python 3.13.5. The suite includes category shortfalls, rejection of an in-scope question masquerading as an out-of-scope one and live-independent workflow checks.
- Qwen2.5 3B was absent from the local model store. Its initial pull to the regular model store failed because the sandbox denied opening a partial blob. An isolated local Ollama server on port 11440 uses a writable workspace cache, with 4.9 GiB RAM free after unloading Gemma. The pull is in progress. No Qwen results have been recorded yet.

The requester took over model installation. Stopped the scratch Qwen pull, its local server and the queued probe. The partial download was preserved in the workspace cache. Install qwen2.5:3b in the normal Ollama store before resuming. No Qwen inference or full live evaluation scores are available yet.


## Groq Free Plan integration

- Added an optional Groq transport in llm.py using project-root .env or GROQ_API_KEY from the environment. Existing local Ollama configurations still load. Hosted configs save a groq: model reference and never store credentials.
- GPT-OSS 120B generates requirements, designs, cases and answers. GPT-OSS 20B separately judges the answers. A live header check matched the published Free Plan quotas of 1,000 requests per day and 8,000 tokens per minute. The first HTTP 403 came from Cloudflare error 1010 for the default urllib client identifier. ForgeAI now sends its own client identifier.
- The first academic run hit HTTP 429 after accepting 15 drafts. Rate-limit retries now use bounded backoff. The CLI resumed the academic drafts, froze 20 cases and measured the pilot baseline at 8 passed, 12 failed and 0 infrastructure errors.
- The pilot exposed evaluation quality issues. Some positive questions stretched the narrow academic brief and some ambiguous questions asked the user to identify an omission. The judge occasionally gave conflicting refusal and citation flags for correct answers or safe abstentions. Tightened semantic review and ambiguity prompts, added a separate broader academic factory brief for future runs, and moved mechanically knowable checks to code. The pilot cases remain frozen and its scores retain the original judge behavior.
- The original procurement attempt was interrupted after five accepted drafts to reduce Free Plan token contention. The partial artifacts remain under artifacts/groq-procurement.
- Regression tests after these changes returned 40 passed in 4.39 seconds. These include mocked Groq request, authorization and rate-limit checks, draft resume, and deterministic refusal scoring. Live demo evidence is tracked separately.

### Live quota and fallback checkpoint

- The earlier academic pilot measured 8/20 at baseline and 9/20 after one targeted patch. Its weaker rubric and cases are retained separately.
- The revised Groq runs each scored 12/20 at baseline on 20 frozen cases. The baselines each include seven semantic failures and one infrastructure error. The daily GPT-OSS 120B token cap interrupted version 1. Academic retained 6/20 results and procurement retained 13/20. There are no full version 1 scorecards.
- Confirmed the SHA-256 fingerprints and exact per-case records against both frozen datasets. Verified academic chat 3/3 with GPT-OSS 20B. Verified procurement CSV plus calculator and the standalone CSV routing regression with GPT-OSS 120B.
- NVIDIA's free Nemotron 3.5 Lightning endpoint returned a valid JSON response. Added an explicit NVIDIA model prefix and bounded host-specific retries. A fresh NVIDIA run uses its own artifact directory.

- Final regression suite: 41 passed in 4.22 seconds. The live NVIDIA adapter passed Pydantic validation and built a procurement agent. Its evaluation had accepted 5 drafts at the reporting checkpoint. No NVIDIA score was observed.
