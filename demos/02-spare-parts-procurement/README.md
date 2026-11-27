# Spare-parts procurement assistant

Helps procurement staff find catalogue items and interpret supplier terms. The saved tool smoke test shows CSV lookup and calculator use.

## Evaluation scorecard

| Version | Passed | Failed | Errors | Pass rate | Δ vs baseline | Selection |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| [Baseline (v0)](EVIDENCE.md#scorecards-and-optimization) | **12/20** | 7 | 1 | **60%** | — | **Retained** |
| [Iteration 1 (v1)](EVIDENCE.md#scorecards-and-optimization) | **11/20** | 9 | 0 | **55%** | -5 pp | Not retained |

The baseline’s one error was a judge rate limit. Iteration 1 adjusted tool-selection instructions. [Final report](../../backend/artifacts/groq-procurement-final/final_report.md)

[Review the run evidence](EVIDENCE.md) for the requirements, tool choices, optimization decision, examples, and all 20 case outcomes in GitHub-readable tables.

| Evidence | Files |
| --- | --- |
| Inputs | [Requester brief](../../backend/demo_data/procurement_brief.txt), [source documents](../../backend/demo_data/procurement/), [document synthesis prompt](../../backend/demo_data/procurement_synthesis_prompt.txt) |
| Requirements | [Structured requirements](../../backend/artifacts/groq-procurement-final/requirements.json), [groundability review](../../backend/artifacts/groq-procurement-final/coverage.json), [document manifest](../../backend/artifacts/groq-procurement-final/document_manifest.json) |
| Generated agent | [Retained agent definition](../../backend/artifacts/groq-procurement-final/agent_config.json), [version snapshots](../../backend/artifacts/groq-procurement-final/versions/) |
| Frozen evaluation | [20 generated cases](../../backend/artifacts/groq-procurement-final/eval_dataset.json), [evaluation generation prompt](../../backend/forgeai/prompts/eval_generate.txt), [supporting prompt files](../../backend/forgeai/prompts/) |
| Case results | [Baseline v0](../../backend/artifacts/groq-procurement-final/case_results/v0.json), [iteration v1](../../backend/artifacts/groq-procurement-final/case_results/v1.json) |
| Optimization | [Iteration log](../../backend/artifacts/groq-procurement-final/iteration_logs.json), [scorecards](../../backend/artifacts/groq-procurement-final/scorecards.json) |
| Run record | [Metadata](../../backend/artifacts/groq-procurement-final/run_metadata.json), [all saved artifacts](../../backend/artifacts/groq-procurement-final/) |
