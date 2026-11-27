# Museum collections assistant

Answers collections staff questions about loan intake, storage, object movements, and incident procedures.

The baseline passed **13/20**. The first iteration clarified scope and disambiguation instructions and passed **14/20**, so **v1** was retained. Both versions recorded zero infrastructure errors. [Final report](../../backend/artifacts/groq-museum-rehearsal-r2/final_report.md)

| Evidence | Files |
| --- | --- |
| Inputs | [Requester brief](../../backend/demo_data/museum_rehearsal_brief.txt), [source documents](../../backend/demo_data/museum_rehearsal/), [document synthesis prompt](../../backend/demo_data/museum_rehearsal_synthesis_prompt.txt) |
| Requirements | [Structured requirements](../../backend/artifacts/groq-museum-rehearsal-r2/requirements.json), [groundability review](../../backend/artifacts/groq-museum-rehearsal-r2/coverage.json), [document manifest](../../backend/artifacts/groq-museum-rehearsal-r2/document_manifest.json) |
| Generated agent | [Retained agent definition](../../backend/artifacts/groq-museum-rehearsal-r2/agent_config.json), [version snapshots](../../backend/artifacts/groq-museum-rehearsal-r2/versions/) |
| Frozen evaluation | [20 generated cases](../../backend/artifacts/groq-museum-rehearsal-r2/eval_dataset.json), [evaluation generation prompt](../../backend/forgeai/prompts/eval_generate.txt), [supporting prompt files](../../backend/forgeai/prompts/) |
| Case results | [Baseline v0](../../backend/artifacts/groq-museum-rehearsal-r2/case_results/v0.json), [iteration v1](../../backend/artifacts/groq-museum-rehearsal-r2/case_results/v1.json) |
| Optimization | [Iteration log](../../backend/artifacts/groq-museum-rehearsal-r2/iteration_logs.json), [scorecards](../../backend/artifacts/groq-museum-rehearsal-r2/scorecards.json) |
| Run record | [Metadata](../../backend/artifacts/groq-museum-rehearsal-r2/run_metadata.json), [all saved artifacts](../../backend/artifacts/groq-museum-rehearsal-r2/) |
