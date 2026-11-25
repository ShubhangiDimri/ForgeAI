# ForgeAI implementation status


## Groq integration and live verification checkpoint

The complete factory can use a Groq Free Plan key in the ignored project-root .env.
The default hosted agent uses GPT-OSS 120B and the separate judge uses GPT-OSS 20B.
The local Ollama path and locally cached MiniLM embeddings remain available. The
successful authenticated call reported 1,000 requests per day and 8,000 tokens per
minute, matching the Free Plan.

| Requirement | Current verification |
| --- | --- |
| 1. Intake | Live unattended briefs produced requirements.json on both domains. See forgeai/intake.py and each final run directory. The interactive path and question limit have scripted coverage. |
| 2. Groundability | Both live builds wrote coverage.json before generating their designs. forgeai/coverage.py preserves evidence and identifies unsupported and inconclusive topics. |
| 3. Agent generator | Both live builds saved dynamic agent definitions with tool selections. The procurement tool check used the generated configuration and executed CSV lookup and calculator, returning 127.50 USD. See forgeai/generator.py, forgeai/tools.py and artifacts/groq-procurement-final/tool_smoke.json. |
| 4. Evaluation generation | forgeai/evaluation.py and forgeai/prompts generated live frozen cases. The original academic pilot revealed scope and ambiguity issues. Category-specific review prompts and draft resume were exercised in the revised runs. |
| 5. Judge | forgeai/judge.py combines model evaluation with evidence, refusal, citation and tool checks. The pilot recorded a full baseline and an optimized scorecard. Revised rules avoid mechanically inconsistent refusal and citation flags found in the pilot. |
| 6. Critic and optimizer | forgeai/optimizer.py and forgeai/workflow.py ran one measured targeted pilot iteration. It improved from 8/20 to 9/20 under the original rubric. Scripted integration tests cover additional iteration, classification, rollback and rechunking behavior. |
| 7. Reports | The pilot quality report and scorecards preserve 20 scored cases per measured version, the original rubric and the source dataset hash. Individual execution records are under case_results. |
| 8. Runnable product | forgeai/runner.py loads hosted and local definitions. Gemma answered/refused the three academic smoke questions. GPT-OSS successfully executed both tools in the procurement smoke. |
| 9. Two full demonstrations | The revised academic and procurement runs have independent synthetic data, brief, requirements and generated agent snapshots. The current run artifacts are under artifacts/groq-academic-final and artifacts/groq-procurement-final. Completion is determined by the run metadata and measured scorecards. |

The earlier checklist and Phase A audit below are historical. The pilot's measured
improvement is a workflow observation. Several pilot evaluation cases were weak,
so its scores should not be used as a comparison against the revised rubric. The
assignment describes a small open runtime model. The historical small local model
smoke checks and the hosted GPT-OSS full runs are separate evidence. A full small
local-model evaluation remains unverified.

### Live scores and blocker

| Groq run | Baseline | Targeted rerun |
| --- | --- | --- |
| Academic | 12 passed, 7 failed, 1 execution error | 6/20 recorded. Final score unmeasured. |
| Procurement | 12 passed, 7 failed, 1 judge error | 13/20 recorded. Final score unmeasured. |

Both frozen datasets contain 20 distinct cases in five categories. Both baseline
scorecards were checked against their raw cases and dataset hashes. Groq's
GPT-OSS 120B reached the Free Plan 200,000 daily token cap. The baseline remained
selected in each revised Groq run. The academic smoke passed all three checks.
The procurement agent returned 127.50 USD using CSV lookup and calculator.
A subsequent live regression check returned 27.25 USD with CSV lookup alone.
That runtime fix did not change the frozen evaluation cases or past scores.

NVIDIA support uses a separate provider and run directory. The free
Nemotron 3.5 Lightning endpoint returned valid JSON using NVIDIA_API_KEY.
The old GPT-OSS 20B free NVIDIA endpoint returned HTTP 410. The live NVIDIA procurement build saved its runnable agent in artifacts/nvidia-procurement. It had accepted 5 evaluation drafts at the reporting checkpoint. No NVIDIA scorecard had been measured. The final regression suite returned 41 passed in 4.22 seconds, with mocked provider transport tests. Requirement 9
remains open until two complete live runs are recorded.

## Current development checkpoint

The following table supersedes the earlier Phase A audit retained below. Prototype smoke execution and procurement tool routing are verified. Evaluation and optimization are implemented and tested with scripted model outputs. The live Gemma attempts stopped before a frozen dataset and produced no baseline or optimization scores.

| OceanAI requirement | Status and evidence |
| --- | --- |
| 1 Intake | Implemented. `forgeai/intake.py` filters preference questions, bounds and deduplicates them, records unanswered requests and preserves explicit topics. Existing intake tests and the unattended CLI test passed. Live question relevance remains model-dependent. |
| 2 Groundability | Implemented before design. `forgeai/coverage.py` and `generator.py` distinguish confirmed out-of-retrieval evidence and inconclusive reviews from unsupported topics. Unit fixtures verify partial and invalid evidence; Phase A saved evidence verifies a true exclusion. |
| 3 Agent generator | Implemented. `generator.py`, `schema.py` and `tools.py` generate and enforce settings and tool selections. A unit integration test executes CSV lookup followed by the calculator. Direct Open-Meteo call returned a live response. A fresh Gemma trace verified both CSV lookup and calculator, returning the correct 127.5 USD in artifacts/full-procurement/tool_smoke_after_fix.json. |
| 4 Evaluation generation | Implemented and tested with scripted model outputs. `evaluation.py`, `prompts/eval_generate.txt` and `prompts/eval_validate.txt` generate, verify and freeze at least 20 cases across five categories. The model must pass evidence, category and tool-intent checks before freezing. Live attempts validated individual batches but did not complete a dataset. |
| 5 Judge | Implemented and tested in fixtures. `judge.py` and `prompts/judge.txt` combine independent semantic assessment with deterministic checks. Shared-model bias remains a limitation with the default judge. |
| 6 Critic and optimization | Implemented. `judge.py`, `optimizer.py`, `runner.py` and `workflow.py` classify all four categories, measure bounded targeted changes, rebuild chunks and index, and roll back regressions. Scripted integration tests measured baseline plus three iterations. |
| 7 Honest reporting | Implemented. `workflow.py` records per-case results, scores, actual patches and stop reasons. The scripted integration test verifies persisted versions and best selection. Live report artifacts are pending. |
| 8 Runnable product | Verified on the saved academic agent. `__main__.py` and `runner.py` reload it and answer documented CLI questions. Fresh Gemma rerun passed 3/3 in `artifacts/phase1-smoke/smoke.json`. |
| 9 Two full demonstrations | Procurement and academic inputs exist. Both full CLI commands generated runnable agents. Live evaluation retries exposed invalid questions and did not reach the scoring stage. Incomplete attempts and the successful procurement tool probe are retained under artifacts. Two complete demonstrations remain open. |

Regression command `python -B -m pytest -q -p no:cacheprovider` returned **35 passed in 4.24s**. These tests substitute model output and embeddings where appropriate. Full demo commands and artifact descriptions are in README.md. Phase notes are in DEVELOPMENT_PROGRESS.md. Python 3.11 remains unverified. Gemma used pre-existing dependencies and weights. Qwen2.5 3B was selected for a short comparison. The partial workspace download was stopped at the requester's direction. Manual installation is pending.

## Historical Phase A audit

**Audit date** · 25 November 2026  
**Project** · `C:/Users/shubh/OneDrive/Desktop/ForgeAI`  
**Assessment basis** · Original OceanAI campus recruitment assignment, pages 1–3. `PROJECT_SPEC.md` and `ForgeAI_Requirements.docx` are internal planning references. The audit inspected source, prompts, configuration, data, generated JSON, local dependencies and test evidence.

## Executive status

ForgeAI has a working Phase A build-and-chat prototype demonstrated on one synthetic academic dataset. Its final saved run answered the supported attendance question with a citation and refused both the unsupported scholarship question and an unrelated geography question. The code generates agent definitions dynamically. Intake quality, tool relevance, grounding robustness and unseen-domain behavior remain open. Evaluation generation, judging and autonomous optimization are absent. The current project does not satisfy the complete nine-requirement assignment.

In this report, **tested** means an observed test passed within the stated scope. **Partial** means some required behavior is missing or the observed output exposed a gap. **Unverified** means available evidence does not establish the behavior. **Not started** means no implementation or deliverable was found.

## 1. Project layout

```text
ForgeAI/
├── AGENTS.md
├── ForgeAI_Requirements.docx
├── PROJECT_SPEC.md
├── PROJECT_STATUS.md
├── README.md
├── requirements.txt
├── pytest.ini
├── .gitignore
├── forgeai/
│   ├── __init__.py
│   ├── __main__.py
│   ├── documents.py
│   ├── retrieval.py
│   ├── intake.py
│   ├── coverage.py
│   ├── generator.py
│   ├── tools.py
│   ├── runner.py
│   ├── schema.py
│   ├── llm.py
│   └── prompts/
│       ├── boundary.txt
│       ├── questions.txt
│       ├── requirements.txt
│       ├── design.txt
│       ├── coverage.txt
│       ├── route.txt
│       └── answer.txt
├── demo_data/
│   ├── brief.txt
│   ├── synthesis_prompt.txt
│   └── academic/
│       ├── attendance.txt
│       ├── assessment.txt
│       └── offices.csv
├── tests/
│   ├── __init__.py
│   ├── test_factory.py
│   ├── test_evidence.py
│   └── smoke_live.py
└── artifacts/
    ├── academic/
    ├── academic-v2/
    └── academic-final/
```

Each artifact directory contains `requirements.json`, `coverage.json`, `document_manifest.json`, `agent_config.json`, `corpus.json` and `smoke.json`. `academic-v2` also contains `smoke-before-routing-fix.json`. Existing disposable directories are `.pytest_cache/`, `forgeai/__pycache__/` and `tests/__pycache__/`. No local virtual environment or Git worktree was detected. The assignment PDF is outside the project root in Downloads.

## 2. Stack, dependencies and models

The CLI uses Python and argparse. The target is Python 3.11 and the inspected executable is Windows x64 Python **3.13.5**. The 3.11 setup and compatibility remain unverified on this host. Ollama is installed locally. The prior live run reported Ollama **0.14.3**. The application talks to Ollama over HTTP using the standard library.

| Dependency | Declared in requirements.txt | Installed | Role |
| --- | --- | --- | --- |
| Pydantic | >=2.7,<3 | 2.13.5 | Structured requirements, config, model responses and tool arguments |
| pandas | >=2,<4 | 2.3.2 | CSV ingestion |
| faiss-cpu | >=1.8,<2 | 1.15.0 | Exact CPU vector search |
| sentence-transformers | >=3,<6 | 5.2.0 | Local sentence embeddings |
| PyMuPDF | >=1.24,<2 | 1.27.2.3 | PDF text extraction |
| pytest | >=8,<10 | 8.3.0 | Unit suite |
| NumPy | Resolved through installed dependencies | 2.3.1 | Vector arrays, imported directly by retrieval |
| PyTorch | Resolved through installed dependencies | 2.10.0 | Embedding runtime |
| Transformers | Resolved through installed dependencies | 4.53.2 | Embedding model support |

The dependency ranges permit installer variation. There is no lockfile. No frontend, paid API integration or external database appears in the code.

- **LLM default** · `qwen2.5:3b` via `forgeai/__main__.py`. Build accepts `--model` or `FORGE_MODEL`. Qwen was absent from the inspected local Ollama model manifests.
- **LLM exercised** · All three saved runs specify `gemma2:2b`. Chat takes the model from the saved configuration. Setting `FORGE_MODEL` on a chat command has no effect on that definition.
- **Embedding** · All saved runs use `sentence-transformers/all-MiniLM-L6-v2`. Its local snapshot is present. Prior execution produced 384-dimensional embeddings. Build accepts `--embedding` or `FORGE_EMBEDDING`. Chat uses the saved value. Weights load offline on CPU with remote model code disabled.
- **Other installed Ollama model** · `nomic-embed-text:latest` exists in the model store. ForgeAI uses Sentence Transformers for embeddings.
- **Environment check** · Approximately 15.34 GiB RAM total, 4.04 GiB free and 689 GiB disk free at audit. Prior live work began with roughly 1.14 GiB RAM free. TCP connections to ports 11434 and 11439 failed during this audit. The prior run used 11439. Start a reachable Ollama endpoint before running live commands. No fresh LLM call was made for this report.

## 3. Architecture and execution flow

### Build

1. `forgeai/__main__.py` parses the brief and document path. The currently exposed build mode requires `--prototype-only`. `generator.py` requires a fresh output directory outside the corpus.
2. `documents.py` recursively loads the supported inputs into typed passages and hashes the original files.
3. `intake.py` sends the brief and up to two 450-character excerpts per file to generate a batch of at most five questions. In unattended mode it records unanswered questions without reading stdin. A second model call extracts requirements from the brief and answered questions. A deterministic pattern preserves explicit English topic lists, and inferred audience and tone can be recorded as assumptions.
4. `generator.py` asks the model for agent guidance, retrieval settings and tool proposals. Pydantic validates their shape. The generator checks availability, applies the capability filter from `tools.py`, chunks the corpus and builds a FAISS index.
5. `coverage.py` assesses each must-answer topic against retrieved sentence candidates. The model selects numbered sentences and a coverage status. The factory copies the actual text and chunk IDs. Invalid selections and empty retrieval fail closed. Unsupported topics are appended to must-refuse before the definition is saved.
6. The generator stages five JSON artifacts and renames the staged directory into place after successful processing. The definition embeds requirements, coverage, model IDs, settings, manifest, answer schema and the corpus hash.

### Saved-agent chat

1. `runner.py` validates the config and the adjacent `corpus.json`, verifies its digest and rebuilds the vector index. The original documents are unnecessary for chat when the snapshot is intact.
2. It blocks literal restricted phrases, retrieves passages and asks Ollama to route the question. The routing step receives scope, coverage, generated guidance, evidence and tool schemas. For a document-only agent, the route schema permits a null tool only.
3. A permitted tool call adds evidence or yields a refusal when lookup returns no rows. The runner refuses when no evidence is available. Otherwise, Ollama produces an `Answer` with text, citation IDs and a refusal flag. A substantive answer needs at least one citation and every returned citation ID must be present in the supplied evidence.
4. `llm.py` supplies a shared untrusted-data boundary and separate stage prompts. Calls use schema-constrained JSON, a 4,096-token context, up to 640 generated tokens, four threads, temperature zero and a 240-second HTTP timeout. Invalid structured output can receive one retry. Connection and HTTP failures exit immediately with an error.

## 4. Ingestion, chunking and retrieval

| Layer | Current behavior | Evidence and scope |
| --- | --- | --- |
| PDF | PyMuPDF text extraction per page, with 1-based page metadata. A page with no extractable text fails ingestion. | `documents.py`, `test_loader_and_provenance` and invalid-input cases. PDF loading is unit-tested with generated fixtures. No PDF was used in the saved live corpus. |
| CSV | pandas loads columns as strings, retains leading zeroes and preserves empty fields. Each 1-based data row becomes a passage with `column=value` text and original cell mapping. | `documents.py`, loader and lookup tests, two rows in every live `corpus.json`. |
| TXT | UTF-8 with BOM handling. Initial passage covers the file. | `documents.py`, loader test and both live policy documents. |
| Provenance | Relative name and locator yield IDs such as `policy.pdf#p2:c1`, `offices.csv#r1:c1` and `attendance.txt#text:c1`. Original files and the serialized corpus have SHA-256 digests. | `documents.py`, `generator.py`, `runner.py`. Audit verified the corpus hash, manifest agreement and current source hashes for all three saved runs. |
| Chunking | Whitespace word windows that stay within original PDF pages, CSV rows or TXT files. Size range 24–180 words. Stride is size minus overlap. | `documents.py`, `schema.py`, overlap and provenance tests. Final live corpus uses size 180, overlap 0. Its short inputs do not exercise overlapping live chunks. |
| Embeddings and search | Sentence Transformers produces contiguous float32 vectors. FAISS normalizes corpus and query vectors and searches `IndexFlatIP` by cosine similarity. The configured `top_k` and `min_score` control hits. | `retrieval.py`, real FAISS with deterministic encoder in the unit suite, real MiniLM and FAISS in saved live work. Final run uses top_k 1 and cutoff 0.30. |

The loader rejects missing or empty document folders and unsupported extensions. Corrupt PDFs and textless PDF pages surface as errors. There is no OCR, hybrid retrieval, reranking or persisted vector index. Chat loads the already chunked snapshot, so editing chunk size or overlap in an existing definition does not rechunk it. Rebuild to apply changes to those parameters.

## 5. Dynamic configuration and tools

`generator.py`, `schema.py` and `prompts/design.txt` implement dynamic generation. The model proposes the domain guidance, chunking, retrieval and candidate tools. The program defines validation ranges, supported tool names and the standard answer schema. The actual answer validator is the runtime `Answer` class. The saved `output_contract` is descriptive metadata and editing it cannot redefine the runner contract. The same academic brief yielded different settings and tool lists over three builds. This demonstrates generated values but does not establish generalization across domains.

| Tool | Implementation and enforcement | Verification |
| --- | --- | --- |
| `csv_lookup` | Exact file, column and value matching over saved CSV cells. Returns matching chunk IDs and text. The model cannot pass an arbitrary filesystem location to be opened. | Unit test checks an exact string identifier with a leading zero. Live final build correctly omitted it. Successful model-driven use remains unverified. |
| `calculator` | Add, subtract, multiply and divide on two validated finite floats, with finite result validation. Uses operator functions. | Unit tests verify multiplication and rejection of expression-shaped arguments. Live execution remains unverified. |
| `current_date` | Empty argument object. Returns ISO date from the execution host. | Unit test exercises allowlist rejection. Successful execution and model-driven use remain unverified by the available tests. |
| Keyless public HTTP API | Absent. The Phase A scope treated weather as optional. The assignment's Data & assets section also lists a keyless public API among registry choices, so this remains a submission coverage gap to resolve. | `schema.py` and `tools.py` enumerate three local tools. |

The builder makes CSV lookup available only when it loaded CSV rows. It filters model proposals using English capability terms in the brief and must-answer topics. `runner.py` supplies selected schemas and calls `tools.execute()`, which checks the allowlist and validates arguments before dispatch. Runner uses at most one tool per question. Claimed tool relevance is partly heuristic. Live evidence covers exclusion and a blocked call, while positive attachment and invocation remain unverified end to end.

## 6. OceanAI mandatory requirements

| # | Requirement | Status and available evidence |
| --- | --- | --- |
| 1 | Intake interviewer | **Implemented, tested in part.** `intake.py`, `schema.py`, `prompts/questions.txt` and `prompts/requirements.txt` implement structured intake and a maximum of five questions. Mocked tests cover the bound, deduplication, answered input and unattended unresolved recording. Final live `requirements.json` contains all core fields and original topics. It also includes two paraphrased duplicates, factual questions recorded as unresolved and an inferred formal tone despite the concise brief. Live interactive interview and turn-by-turn adaptation are unverified. |
| 2 | Groundability guard | **Implemented, tested for the demo.** `coverage.py` and `generator.py` bind selected sentence numbers to corpus evidence and append unsupported topics to refusal requirements. Mocked tests cover partial coverage and invalid evidence selection. Final `coverage.json` supports attendance and reassessment and restricts scholarship eligibility. The earlier `academic-v2` build falsely restricted reassessment. Live partial-topic handling and robustness across domains remain unverified. The model drafts the design before coverage runs. Restrictions are incorporated before the final definition is published. |
| 3 | Agent generator | **Implemented, tested in part.** `generator.py`, `schema.py`, `tools.py` and `prompts/design.txt` generate the prompt, settings, tool proposals and reasons, then write the complete config with output contract and manifest. Saved runs and schema tests verify structured output. Final policy config attaches no unnecessary tools. The earlier run invented CSV relevance. Tool-positive live generation and unseen briefs remain unverified. |
| 4 | Automatic evaluation dataset | **Not started.** No generator, generation prompt or generated evaluation dataset was found. `tests/smoke_live.py` contains three hand-written academic checks. The assignment requires at least 20 generated cases with expected sources and facts, refusal cases and ambiguous and multi-document edge cases. |
| 5 | Automated judge | **Not started.** `runner.py` checks citation membership and the smoke script checks expected refusal, an attendance value and source prefix. No per-case grounding, correctness and refusal judge or bias mitigation exists. |
| 6 | Critic and optimizer | **Not started.** No automatic failure classification, targeted change engine, frozen evaluation reruns, three-iteration cap or change and score logs exist. Saved academic revisions came from manual development. |
| 7 | Honest reporting | **Partial.** `generator.py` saves agent definitions and coverage. `tests/smoke_live.py` saves case responses, errors and booleans. Saved files retain prior failures. The factory has no evaluation scorecards or generated final quality report with remaining failures and reasons. This status report is an audit. |
| 8 | Runnable product | **Implemented and tested on the academic agent.** `__main__.py`, `runner.py`, `retrieval.py` and `tools.py` reload and execute saved definitions. Unit and saved live evidence covers supported, unsupported and out-of-scope questions. Broader generated-config compatibility and a successful live tool call remain unverified. |
| 9 | Two complete demonstrations | **Partial.** One distinct prototype domain and three revisions are present under `artifacts/`. They share the brief and source files. Zero complete assignment demonstrations with generated evals, iteration logs and scorecards were found. Git did not identify this directory as part of a repository, so there is no local commit evidence. |

## 7. Datasets and artifacts

- **Academic corpus** · A synthetic North Quay Institute dataset created for Phase A. `attendance.txt` gives the 75% attendance rule and appeal deadline. `assessment.txt` gives one reassessment attempt and a registration window. `offices.csv` lists two fictional offices. Scholarship eligibility is intentionally absent.
- **Brief and synthesis provenance** · `demo_data/brief.txt` requests a concise student policy assistant. `demo_data/synthesis_prompt.txt` records the corpus-generation brief. No real institutional documents were found in the runtime demo corpus. The assignment PDF and internal planning documents serve as project references outside that corpus.
- **Unit fixtures** · Tests generate tiny temporary PDF, CSV and TXT inputs, including empty, corrupt, unsupported and textless cases. Scripted model outputs and deterministic vector fixtures support orchestration tests.
- **Smoke cases** · The three handwritten prompts live in `tests/smoke_live.py`. Their JSON outputs are execution records. Earlier snapshots preserve distinct settings and results. None contains a generated evaluation dataset or optimizer run.

## 8. Verified test evidence

**Current audit unit rerun** · `python -B -m pytest -q -p no:cacheprovider` returned **14 passed in 7.67s** under Python 3.13.5. The previous README records **14 passed in 6.58s**. Tests run real parsing, validation, arithmetic, CSV logic and FAISS search. They substitute the encoder, Ollama responses or HTTP transport where appropriate. `test_factory.py` covers provenance, invalid inputs, retrieval settings, schemas, allowlist, retries and saved-agent orchestration. `test_evidence.py` covers partial and invalid model evidence, scripted interactive input and relevance filtering.

**Saved real-model execution** · Verified by inspecting the historical JSON. The audit did not repeat the live calls.

| Artifact | Supported attendance | Unsupported scholarship | Out-of-scope geography |
| --- | --- | --- | --- |
| `academic/smoke.json` | Failed with wrongful refusal | Passed | Passed |
| `academic-v2/smoke-before-routing-fix.json` | Failed with `Tool not permitted: csv_lookup` | Passed | Passed |
| `academic-v2/smoke.json` | Passed, 75 percent with attendance citation | Passed | Passed |
| `academic-final/smoke.json` | Passed, 75% with `attendance.txt#text:c1` | Passed | Passed |

Final `coverage.json` identifies evidence for one reassessment attempt. The smoke runner did not ask a reassessment question, so this is coverage evidence only. The three cases establish the observed behavior on those inputs and do not measure generalized accuracy. Python 3.11, Qwen2.5 3B, successful live tool use, live PDF ingestion, adversarial documents, ambiguous or multi-document queries and an unseen-domain build remain unverified.

## 9. Defects, limitations and blockers

| Finding | Evidence and impact |
| --- | --- |
| Intake can misread intent | Final requirements repeat paraphrased topics and include factual clarifications. A single batch of questions limits adaptation. Narrow English list parsing and sparse first excerpts can miss scope or exclusions. |
| Coverage mixes retrieval and entailment | A cutoff miss becomes unsupported. A wrong semantic decision can reject a valid rule, as seen for reassessment in the second build. Valid sentence numbers establish provenance. The final attendance finding also includes an appeal sentence, showing that direct relevance is model-dependent. |
| Scope and facts remain model-dependent | Literal refusal checks can miss paraphrases or block a relevant question containing a restricted phrase. Prompts and routing support scope enforcement, but citation membership alone cannot establish factual entailment. Even a refusal can contain supplied citations because the schema only requires citations on substantive answers. |
| Prompt injection resistance is unverified | Prompts tell the model to treat document and tool data as untrusted. Tool names, arguments and citations also have code checks. No adversarial document suite was found. |
| Tool error recovery is limited | The executor raises on unauthorized tools, invalid arguments and division by zero. The CLI handles errors at the command boundary, so a failed chat question can end the session. CSV output has no result cap and repeated long-row chunks may all match. |
| Context and dataset size | Input size has no explicit token budgeting. Large corpora, broad retrieval or long CSV fields can overflow or truncate a small context. In-memory encoding and reindexing add startup cost. |
| Runtime reproducibility | Only Python 3.13.5 and Gemma have live evidence. Qwen is missing locally, dependencies are range-based and both observed ports were unreachable during the audit. A prior Ollama call timed out, and the original Phase A logs include a transient Windows FAISS DLL load failure. The current unit rerun passed. |
| Layout and interface limits | OCR, persistent conversation state, a full build pipeline and an evaluation CLI are absent. The no-existing-output rule prevents accidental replacement but requires a fresh run directory. |

## 10. Exact PowerShell commands

The following commands use the current machine's installed Python, cached MiniLM and installed Gemma. Start Ollama in a separate PowerShell terminal if the default endpoint is unavailable.

```powershell
ollama serve
```

Then run from the project root. Use a fresh path if `audit-demo` already exists.

```powershell
Set-Location 'C:\Users\shubh\OneDrive\Desktop\ForgeAI'
$env:FORGE_OLLAMA_URL = 'http://127.0.0.1:11434'
ollama list
$brief = (Get-Content -Raw .\demo_data\brief.txt).Trim()

python -m forgeai build --prototype-only --non-interactive --model gemma2:2b --brief "$brief" --docs .\demo_data\academic --out .\artifacts\audit-demo
python -m forgeai chat --config .\artifacts\audit-demo\agent_config.json
python -m forgeai chat --config .\artifacts\academic-final\agent_config.json --question "What is the minimum attendance per taught module?"
python -B -m pytest -q -p no:cacheprovider
python -m tests.smoke_live .\artifacts\audit-demo\agent_config.json
```

Omit `--non-interactive` for the CLI interview. Enter `/quit` or a blank line to exit chat. The smoke command writes or overwrites `smoke.json` beside the chosen definition. Run it against a fresh generated folder to preserve the existing evidence.

If 11434 is unavailable, the historic setup used an alternate port. In the server terminal, use the following.

```powershell
$env:OLLAMA_HOST = '127.0.0.1:11439'
$env:OLLAMA_MODELS = 'C:\Users\shubh\.ollama\models'
ollama serve
```

In the client terminal, set both variables and skip the previous assignment to port 11434.

```powershell
$env:OLLAMA_HOST = '127.0.0.1:11439'
$env:FORGE_OLLAMA_URL = 'http://127.0.0.1:11439'
ollama list
```

For the target Python environment on a machine with Python 3.11 registered, run the following. Check available memory and storage before provisioning models. After setup, replace `python` with `& $python` in the build, chat and test commands. Switching the build to Qwen requires provisioning it and using `--model qwen2.5:3b`. The saved academic agent still requires Gemma.

```powershell
py -3.11 -m venv .venv
$python = '.\.venv\Scripts\python.exe'
& $python -m pip install -r requirements.txt
& $python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
ollama pull qwen2.5:3b
```

## 11. Recommended next steps, in priority order

1. **Establish a reproducible baseline.** Verify the Python 3.11 and Qwen setup, capture dependency versions and runtime costs, and repeat the three acceptance cases. Keep the current Gemma run as a reference.
2. **Harden known Phase A failure paths.** Improve question relevance and topic deduplication, distinguish low retrieval confidence from missing facts in coverage evidence, and keep chat usable after recoverable tool errors. Exercise at least one tool-positive brief, live PDFs and a held-out domain. Resolve the keyless API requirement in the registry.
3. **Build the generated evaluation dataset.** Generate and validate at least 20 distinct cases per corpus with expected facts and citation anchors, refusal cases and ambiguous and cross-document queries. Save the prompt and freeze cases before candidate optimization.
4. **Implement scoring and diagnosis.** Combine deterministic checks with a bias-mitigated semantic judge, then classify failures as retrieval miss, prompt defect, hallucination or wrong refusal. Preserve retrieved evidence and tool use in each case trace.
5. **Add targeted optimization and reporting.** Run a measured baseline, apply at most three narrowly scoped iterations against the frozen dataset and save scorecards, change logs, failures and the best measured definition. Connect these stages to the unattended full build.
6. **Produce both submission demonstrations.** Run two substantially different briefs and document sets through the complete pipeline, including the generated tests and optimizer. Preserve all artifacts in a private repository and run a separate unseen-brief rehearsal.

