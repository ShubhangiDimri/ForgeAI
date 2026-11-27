# ForgeAI submission demos

These are the two full runs submitted for the OceanAI assignment. Each demo page links to its original inputs, generated agent, frozen evaluation set, and complete run evidence.

## Evaluation scorecards

| Demo | Version | Passed | Failed | Errors | Pass rate | Δ vs baseline | Selection |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| [Museum collections](01-museum-collections/) | [Baseline (v0)](01-museum-collections/EVIDENCE.md#scorecards-and-optimization) | **13/20** | 7 | 0 | **65%** | — | Not retained |
| [Museum collections](01-museum-collections/) | [Iteration 1 (v1)](01-museum-collections/EVIDENCE.md#scorecards-and-optimization) | **14/20** | 6 | 0 | **70%** | +5 pp | **Retained** |
| [Spare-parts procurement](02-spare-parts-procurement/) | [Baseline (v0)](02-spare-parts-procurement/EVIDENCE.md#scorecards-and-optimization) | **12/20** | 7 | 1 | **60%** | — | **Retained** |
| [Spare-parts procurement](02-spare-parts-procurement/) | [Iteration 1 (v1)](02-spare-parts-procurement/EVIDENCE.md#scorecards-and-optimization) | **11/20** | 9 | 0 | **55%** | -5 pp | Not retained |

pp = percentage points. Errors are counted separately from failed cases.

For a quick review, open the [Museum evidence walkthrough](01-museum-collections/EVIDENCE.md) or the [Procurement evidence walkthrough](02-spare-parts-procurement/EVIDENCE.md). Each includes all 20 case outcomes and links to raw answers, retrieved evidence, and judgments.

Supplementary evidence is available in the [Academic policy run](../backend/artifacts/groq-academic-final/final_report.md) and the [Retail retrieval replay](../backend/artifacts/retail-retrieval-key3-candidate/comparison.md).
