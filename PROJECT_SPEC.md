# ForgeAI — Prototype requirements and acceptance checklist
Source: OceanAI Jr. GenAI Engineer Campus Recruitment Assignment, pp. 1–3. Implementation choices below are proposed, not employer mandates. All items start unverified.

## Goal and scope
Build a domain-independent factory, not a fixed chatbot. Input: one-paragraph brief and a folder of documents. Output: executable declarative agent, generated tests, scorecards and honest quality report. Use a small open model at runtime. Support unseen briefs without source edits. Keep repository private; do not share with other candidates.

## Phase A — first working prototype
- [ ] R1 Intake: inspect documents and brief; ask zero to five adaptive questions; save scope, audience, tone, must-answer and must-refuse topics. Noninteractive mode records assumptions and unresolved gaps without blocking.
- [ ] R2 Groundability: assess each requested topic against document evidence; record supported/partial/unsupported and source IDs. Restrict unsupported topics; never silently invent coverage.
- [ ] R3 Generator: produce validated JSON containing system prompt, chunk size/overlap, retrieval top_k, selected tools with reasons, output contract and document manifest. Reject unknown tools and invalid parameters.
- [ ] R8 Runner: load any generated definition, retrieve evidence, execute only allowed tools, return answer, source IDs and refusal status. Demonstrate supported and unsupported queries.
- [ ] Registry: CSV lookup, calculator, current date, optionally Open-Meteo. Select only needed tools. Use safe arithmetic parsing (no eval), bounded file access and HTTP timeouts.

## Phase B — mandatory before submission
- [ ] R4 Evaluation generator: generate at least 20 distinct cases from source documents, including answerable, out-of-scope/refusal, ambiguous and multi-document cases. Suggested split 10/5/3/2. Store expected facts, source IDs, expected behavior and generation prompt. Verify source evidence; reject invalid cases. Freeze the set before optimization.
- [ ] R5 Judge: score grounding, factual correctness and refusal per case. Check citation IDs and expected evidence deterministically; use an independent rubric-based judge call for semantic checks. Avoid rewarding length, hide agent identity, assess one answer at a time; record remaining bias limitations. Invalid judge output is an error, not a pass.
- [ ] R6 Critic/optimizer: classify every failure as retrieval miss, prompt defect, hallucination or wrong refusal using retrieved evidence and judge results. Apply bounded targeted changes (retrieval settings or specific prompt rules), not full regeneration. Re-run frozen tests after each change, maximum three optimization iterations after baseline. Log changed fields, reasons, affected IDs and before/after scores; retain best measured config and disclose regressions.
- [ ] R7 Report: save final agent definition, baseline and per-iteration scorecards, remaining failures and reasons. Distinguish failed, errored and unrun tests; never invent metrics.
- [ ] R9 Demonstrations: execute two full runs with different briefs and document sets; commit actual requirements, definitions, eval sets, logs, scorecards and reports. Commit synthesis prompts if using synthetic documents. Suggested domains: academic policy PDFs and spare-parts procurement CSV/PDF. Test a third unseen domain separately.

## Proposed implementation
Python 3.11; Ollama with configurable qwen2.5:3b; sentence-transformers with configurable all-MiniLM-L6-v2; FAISS CPU; PyMuPDF; pandas; Pydantic; pytest. CLI first. Confirm compatibility and available RAM/disk before model downloads. Use environment variables for model and endpoint. No paid API dependency by default. Keep dependencies minimal; no LangGraph, frontend or fine-tuning required.

## Interfaces and evidence
Suggested commands (implement and document):
```
python -m forgeai build --brief "..." --docs ./demo_data/academic --out ./artifacts/run1 --non-interactive
python -m forgeai chat --config ./artifacts/run1/agent_config.json
python -m forgeai evaluate --run ./artifacts/run1
pytest -q
```
Build should support interactive intake and an explicit prototype-only option; full build eventually runs evaluation and optimization automatically. Store requirements.json, coverage.json, agent_config.json, document_manifest.json, eval_dataset.json, scorecards.json, iteration_logs.json, final_report.md and configuration snapshots. Use stable document/page/row/chunk identifiers. Keep prompts in versioned text files. Resolve paths relative to run manifest where possible. Never commit secrets, virtual environments or model weights.

## Reliability and acceptance
- [ ] Empty folder, unreadable PDF, unsupported formats, invalid model JSON and unavailable model produce clear errors; bounded retries; no silent success.
- [ ] PDF/TXT/CSV ingestion preserves provenance; scanned PDFs without text are explicitly reported as unsupported in V1.
- [ ] Treat document contents as untrusted data, not instructions. Validate tool inputs and output schema; refuse when evidence is insufficient.
- [ ] Two different briefs produce meaningfully different configurations; no domain-specific branches in factory code.
- [ ] Runner actually loads saved config and produces grounded responses; retrieval settings are honored.
- [ ] Tests cover schema validation, retrieval, unsupported topics, tool allowlist and failure handling. Mocked tests are labeled; at least one real model smoke test required for Phase A.
- [ ] Full submission requires real end-to-end evaluations and both demo runs. Record commands, results and unresolved issues in README.

## Optional only after mandatory requirements
Prompt tournament; token/latency budget; human requirements checkpoint; factory vs human baseline; regression mode; Streamlit/Gradio UI and hosting. These are stretch goals, not Phase A blockers.

## Decisions to confirm before running
- Local project path: __________
- Available RAM / free disk / GPU: __________
- Ollama installed and model available: __________
- Submission deadline: __________
- Demo domains (suggested above): __________
- Phase A status / test evidence: __________
