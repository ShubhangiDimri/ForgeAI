# ForgeAI functional fixes and verification

## Issue-by-issue status

| # | Status | Root cause and change |
| --- | --- | --- |
| 1 | Implemented, live intake observed | Intake dropped questions with a keyword allowlist and could skip a material integration decision. Relevant questions now survive, supplied preferences suppress redundant prompts, and answers are stored and passed into requirement extraction. |
| 2 | Implemented, live requirement observed | An explicit topic-list fallback replaced other requirements. It now merges and deduplicates them. The brief, requester answers and requested behaviors are preserved. A live build inferred hostel residents and retained real-time room availability. |
| 3 | Implemented, live spot check passed | Policy evidence was treated as sufficient for a related subject, and omitted requirements never entered the review. Live state is checked explicitly, applicable registry tools and limitations are surfaced, and new unsupported edits require approval. |
| 4 | Implemented, evidence verified | The checkpoint displayed only the limitation string. It now renders actual source IDs and excerpts as well as the limitation. Batched findings without matching topical evidence fall back to a separate review. |
| 5 | Implemented, API and orchestration tested | The frontend inferred an awaiting status from completed stages. The backend now pauses the actual stage, uses locked transitions, rejects duplicate approvals, and reports measured elapsed times. |
| 6 | Implemented, recovery verified with mocked failures | Independent transports retried without a shared cooldown and an interrupted evaluation could be counted as an error before recovery. Shared cooldown, bounded backoff, four-key Groq rotation, and retry/resume checkpoints now retain completed work. In-progress pre-generation checkpoints are held in memory. |
| 7 | Improved | Embedding models and runners were repeatedly initialized, discovery made one review call per topic, and elapsed time updated only on completion. Encoder and compatible runner reuse, small-corpus review batching, snapshot reuse, and live stage timing reduce duplicate work. Total live runtime still depends on provider capacity and reviews. |
| 8 | Implemented, live fee test passed | The model could select binary operands or unrelated amounts without a source check. A validated sum plan ties inputs to actual source quotes and uses decimal arithmetic. The hostel total was INR 65,000. |
| 9 | Implemented, live fee test passed | Explicit calculator calls returned early with only a bare number and tool citation. Context and tool results now reach synthesis. The verified sum is shown with components and document citations, with the tool in its own activity. |
| 10 | Implemented, live follow-up passed | The UI sent only the latest message. The API now receives bounded, session-specific user turns and pending clarifications. Standalone queries are resolved before retrieval and earlier assistant claims are excluded. |
| 11 | Implemented, live clarification and follow-up passed | Routing had only answer/refuse and mapped missing details to refusal. A focused clarification is a separate outcome and the next turn can resolve the original question. |
| 12 | Implemented, live correction passed | Whole-question routing rejected some relevant questions with unsupported assumptions. Routing and synthesis now treat policy contradictions as grounded corrections and cite the applicable rule. |
| 13 | Implemented, live partial answer passed | Scoped decisions applied to the entire compound question. Bounded retrieval can cover separate clauses, and the answer can include supported information and withhold the unsupported part. |
| 14 | Implemented | No response outcome distinguished clarifications, insufficient evidence, restrictions and partial answers. Validated outcomes feed chat labels, judge expectations and new report summaries. Historical answers continue loading. |
| 15 | Implemented, API and UI regression tests passed | Grounding only controlled sidebar visibility. Off mode now bypasses index loading, retrieval and tools, and reports an unverified request without new citations. Older grounded messages retain citations. |
| 16 | Implemented, mocked Streamlit test passed | Chat state was a per-agent list without a request identity. Reset now assigns a new session and widget ID. Replies with an old ID cannot populate it. Agent, model and grounding selection persist. |
| 17 | Implemented, automated coverage passed, live progress recorded below | The original suite covered single-turn categories with a refusal flag. New runs add five evidence-reviewed behavior cases, use explicit clarification scoring and keep agent/judge models pinned. See live status below. |
| 18 | Implemented, UI payload smoke passed | Source cards used truncated snippets. The source panel now expands full text and distinguishes cited and retrieved passages. Full identifiers are also shown in the conversation header and panel. |

## Code and tests

- `backend/api/main.py` — chat request contract, stateless conversation handoff, grounding bypass, retry and resume routes, stage status, elapsed time and bounded runner cache.
- `backend/forgeai/intake.py`, `coverage.py`, `generator.py`, `schema.py` — requirement provenance, question relevance, live-data boundaries, evidence IDs, approval and reusable build checkpoints.
- `backend/forgeai/runner.py`, `tools.py`, `retrieval.py` — contextual retrieval, partial answers and closure, verified arithmetic, source validation, and shared encoder reuse.
- `backend/forgeai/llm.py`, `workflow.py` — rate limiting, credential rotation, fixed-model evaluation, honest progress and checkpoint recovery.
- `backend/forgeai/evaluation.py`, `judge.py`, `optimizer.py` — evidence-reviewed behavior cases, outcome-aware scoring and targeted changes.
- `backend/forgeai/prompts/` — requirements, interview, coverage batching, context resolution, route, arithmetic, response, judge and behavioral evaluation prompts.
- `streamlit_frontend/app.py` — intake and approval evidence, retry controls, grounding switch, conversation reset, full source inspection and outcome labels. Existing design retained.
- `backend/tests/test_functional_regressions.py` and updated test fixtures — mocked API uploads, grounded input validation, 429 cooldown and key rotation, resumable scoring and build, batched coverage, rewrite and clarification checks.
- `README.md` and `backend/.env.example` — optional fourth Groq key and preferred slot.

## Live evidence

- The original uploaded fee policy states INR 42,000 per semester for double-sharing, INR 18,000 per semester for mess and INR 5,000 once at first admission. Groq returned INR 65,000 with all three components, the verified sum, calculator activity and the fee citation.
- Live Groq calls returned Sunday times of 10 AM to 6 PM with the visitor-policy citation, withheld the personal phone number in a partial response, and corrected the smoking premise with the disciplinary citation.
- Direct questions about live vacancies and unrelated programming returned separate insufficient-evidence and out-of-scope outcomes. A room-type clarification follow-up returned the per-semester double-sharing room fee of INR 42,000 with its source.
- Actual multipart API upload accepted all four files. One interactive 120B build stopped during coverage on 429. A separate 20B build saved an agent after a live requirements checkpoint. Targeted 120B coverage verification with the improved evidence filter selected the fee and visitor documents and marked live availability unsupported.
- The controlled 429, key rotation, retry/resume and Streamlit reset checks use simulated transport or fixtures. Live model responses above came from Groq. The explicit injection override check uses the runtime guard and no model call.

## Final verification snapshot

- Backend pytest passed **78 tests**, with one Starlette test-client warning. A mocked Streamlit AppTest verified history, Grounding OFF, and a new conversation ID with empty history on New chat.
- The live hostel artifact at `backend/artifacts/hostel-functional-final-0ad12c/` froze **25 cases**. At handoff it was **running** (v0: 11 scored cases). Saved scorecards: none yet.
- Use the completed museum run for the measured optimization demo (13/20 to 14/20). Academic and procurement are the two saved assignment demonstrations. The hostel run is a fresh-domain check.

## Restart on Windows

Terminal 1, from the repository root:

```powershell
Set-Location backend
& .\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Terminal 2, from the repository root:

```powershell
$env:FORGEAI_API_URL = 'http://127.0.0.1:8000'
& .\streamlit_frontend\.venv\Scripts\python.exe -m streamlit run streamlit_frontend/app.py
```

## Manual retest

1. Upload the four synthetic hostel TXT files and start an interactive build. Request live availability, citations, a calculator and clarification. Answer the live-source question and check audience, supported sources, missing integration and stage timing on approval.
2. Accept the limitations. Watch the pipeline enter generation and then evaluation. If interrupted, retry or resume from the last saved stage and inspect the real scorecard and optimization log.
3. In Playground, ask Sunday visitor hours plus the warden's personal number, then challenge the smoking rule with the false premise. Inspect the cited excerpts.
4. Ask for the first-semester double-sharing room cost and check the INR 65,000 calculation, fee citation and calculator trace. Ask a follow-up to confirm the context carries.
5. Ask an ambiguous fee question, supply a room type and check that the clarification has its own label. Request live vacancies and unrelated code to check the two refusal outcomes.
6. Disable Grounding, start New chat and ask for a policy fact and the previous question. Verify no fresh sources. Turn Grounding back on and confirm it retrieves sources while the new conversation has no old history.
