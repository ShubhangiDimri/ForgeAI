# ForgeAI

ForgeAI builds a declarative local agent from a brief and a document directory, generates an evaluation dataset and measures targeted configuration changes. A saved run can be moved and opened in a fresh process. Python 3.11 is the target. The current Windows verification used Python 3.13.5.

## Windows PowerShell setup

From the project directory, with Python 3.11 and Ollama installed:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
$python = ".\.venv\Scripts\python.exe"
ollama list
Get-PSDrive C
Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory
```

Start Ollama with `ollama serve` in another terminal if necessary. After checking free resources, provision missing models once:

```powershell
ollama pull gemma2:2b
& $python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
```

## Build, reload and verify

```powershell
$brief = (Get-Content -Raw .\demo_data\brief.txt).Trim()
& $python -m forgeai build --prototype-only --brief $brief --docs .\demo_data\academic --out .\artifacts\my-run --non-interactive
& $python -m forgeai chat --config .\artifacts\my-run\agent_config.json
& $python -m forgeai chat --config .\artifacts\my-run\agent_config.json --question "What is the minimum attendance?"
& $python -m pytest -q
& $python -m tests.smoke_live .\artifacts\my-run\agent_config.json
```

Use a fresh run directory for every build. Omit `--non-interactive` to answer intake questions. Enter `/quit` to end chat. Override the build model with `--model` or `FORGE_MODEL`. Set `FORGE_OLLAMA_URL` to a trusted local endpoint if using a different port. Use `--embedding` for a locally cached Sentence Transformers model or directory. Build and chat load embedding weights offline.

## Modules and artifacts

- `forgeai/documents.py` reads text-bearing PDF pages, UTF-8 text files and CSV rows, then creates word windows with stable source IDs. CSV row numbers start at 1 after the header.
- `intake.py` uses excerpts and the brief to generate clarifications. Blank answers are saved as unresolved.
- `generator.py` generates settings, selects tools and publishes a complete new run after successful validation.
- `retrieval.py` normalizes embeddings and searches FAISS by cosine score with the generated cutoff and candidate count.
- `coverage.py` checks requested topics against retrieval results and verifies quoted evidence. Unverified or absent evidence restricts the topic.
- `tools.py` validates exact CSV lookups, arithmetic and local dates. CSV searches only the run snapshot.
- `runner.py` reloads the saved definition, enforces restrictions and available tools, and validates answer citations. `llm.py` handles schema-constrained Ollama calls. Templates live under `forgeai/prompts/`.
- Each completed build writes `requirements.json`, `coverage.json`, `document_manifest.json`, `agent_config.json` and `corpus.json`. Keep these together. Source SHA-256 hashes describe the original files. The corpus digest detects a mismatched snapshot. Chat rebuilds the in-memory vector index once per session.
- `tests/test_factory.py` runs local unit tests with real parsers and FAISS plus explicit test doubles for generation and embeddings. `tests/smoke_live.py` runs three academic acceptance questions against a real model and stores their results in `smoke.json`.

## Boundaries

Semantic scope, tool relevance and factual entailment depend on the model. Exact citation and quote checks establish provenance but cannot prove every paraphrase. Intake samples two excerpts per file. Large folders, long rows and long conversation inputs can exceed the model context. Chat handles each question independently. Scanned PDFs require external OCR before ingestion. The optional weather capability calls the fixed Open-Meteo endpoint only when selected.

The three academic smoke cases are fixed regression checks. Full factory evaluation generates a separate, frozen case set from the supplied documents.


## Hosted Providers & Fallback

ForgeAI supports local Ollama as well as free-tier hosted endpoints configured via `.env` (gitignored):
- **Groq**: `groq:openai/gpt-oss-120b` / `groq:openai/gpt-oss-20b` (`GROQ_API_KEY`)
- **NVIDIA**: `nvidia:nvidia/nemotron-3.5-lightning-30b-a3b` (`NVIDIA_API_KEY`)
- **Cloudflare Workers AI**: `cloudflare:@cf/meta/llama-3.3-70b-instruct-fp8-fast` (`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`)
- **Fallback**: Use `--model auto` or `FORGE_FALLBACK_PROVIDERS=groq,cloudflare,nvidia` for automatic provider fallback on infrastructure errors.

To resume an interrupted evaluation from saved case results without re-generating the frozen dataset:
```powershell
python -m forgeai evaluate --resume-scoring --run .\artifacts\groq-academic-final
```

## Verified local run, 24 November 2026

Python 3.13.5, installed Gemma 2B via Ollama, cached MiniLM embeddings and CPU FAISS. This machine had 15.34 GiB total RAM, about 1.14 GiB free and about 690 GiB free disk at inspection. Python 3.11 and Qwen were unavailable for verification. No model weights were downloaded.

The final unit run completed with 14 passed in 6.58 seconds. The final real build used the commands above with the system Python, --model gemma2:2b and the output directory artifacts/academic-final. All three live checks passed after reloading the definition. Attendance was answered as 75% with attendance.txt#text:c1. Scholarship eligibility and the unrelated geography question were refused. Coverage also identified the one-attempt reassessment rule in assessment.txt. No tools were selected. Read artifacts/academic-final/smoke.json for the actual responses.

Earlier development runs remain under artifacts/academic and artifacts/academic-v2. The first wrongly refused attendance and selected the directory CSV. The second missed reassessment coverage and initially requested an unauthorized tool, which the runner blocked. The final factory constrains document-only routing and resolves selected evidence sentences to real source IDs. The intake can still duplicate paraphrased topics and ask factual questions instead of useful preference questions. The inferred formal tone was recorded. English capability matching may omit legitimate tools on unusual briefs. Generalization to a second domain, Qwen, and Python 3.11 remain unverified.

## Full factory on Windows

With an existing Ollama server and cached MiniLM, run the commands below from the project root. A new output directory is required for each build. If using the alternate local server, set FORGE_OLLAMA_URL to its address.

```powershell
$env:FORGE_OLLAMA_URL = 'http://127.0.0.1:11439'
$env:OMP_NUM_THREADS = '1'
$academic = (Get-Content -Raw .\demo_data\brief.txt).Trim()
$procurement = (Get-Content -Raw .\demo_data\procurement_brief.txt).Trim()
python -m forgeai build --non-interactive --model gemma2:2b --brief $academic --docs .\demo_data\academic --out .\artifacts\my-full-academic
python -m forgeai build --non-interactive --model gemma2:2b --brief $procurement --docs .\demo_data\procurement --out .\artifacts\my-full-procurement
python -m forgeai chat --config .\artifacts\my-full-procurement\agent_config.json
python -B -m pytest -q -p no:cacheprovider
```

To start the alternate server in a separate PowerShell terminal:

```powershell
$env:OLLAMA_HOST = '127.0.0.1:11439'
$env:OLLAMA_MODELS = 'C:\Users\shubh\.ollama\models'
ollama serve
```

Full builds generate and freeze at least 20 cases across five categories, then measure a baseline and up to three targeted iterations. New builds default to the installed Gemma 2B model. Use --model or FORGE_MODEL to select another installed model. The judge defaults to the agent model. Set --judge-model or FORGE_JUDGE_MODEL to another installed model to assess independently. Keep each run directory intact. Chat loads the selected configuration in the run root. The source snapshot supports actual rechunking. Historical Phase A configs still load without that snapshot.

For a fresh prototype run, add --prototype-only. To evaluate a new prototype with a source snapshot, run python -m forgeai evaluate --run followed by the run path. Evaluation preserves metric files per run and refuses to overwrite an existing evaluation run. Interrupted runs retain available checkpoints.

The keyless weather tool uses the fixed Open-Meteo forecast endpoint. It accepts explicit latitude and longitude and sends only those coordinates and fixed query fields. Its current conditions are in UTC. Calculator and CSV lookup execute locally. See DEVELOPMENT_PROGRESS.md and PROJECT_STATUS.md for observed results and live verification limits.


## Groq Cloud on the Free Plan

ForgeAI can use Groq for chat completions while keeping ingestion, embeddings, retrieval
and tools local. Groq receives the brief, relevant document text and evaluation payloads.
Use synthetic or approved documents. Groq's Free Plan covers both configured GPT-OSS
models within its limits. Use a key from a Free Plan organization for zero usage charges.
Create a project-root .env containing GROQ_API_KEY=your-key. The file is ignored by Git.

From the project root in PowerShell, using a Python environment with the project dependencies
and the cached MiniLM embedding model:

~~~powershell
$academic = (Get-Content -Raw .\demo_data\academic_factory_brief.txt).Trim()
$procurement = (Get-Content -Raw .\demo_data\procurement_brief.txt).Trim()
python -m forgeai build --groq --non-interactive --brief $academic --docs .\demo_data\academic --out .\artifacts\my-groq-academic
python -m forgeai build --groq --non-interactive --brief $procurement --docs .\demo_data\procurement --out .\artifacts\my-groq-procurement
python -m forgeai chat --config .\artifacts\my-groq-academic\agent_config.json
~~~

The default Groq agent and case generator use openai/gpt-oss-120b. The judge uses
openai/gpt-oss-20b. Override with --model groq:<model-id> or --judge-model groq:<model-id>.
Choose fresh output directories for each run. A saved agent remembers its backend through
its model name. Local Ollama builds still use their existing model tags.

If the Free Plan rate limit interrupts evaluation before the dataset is frozen and
the run saved accepted drafts, it can resume in the same folder with unchanged prompts:

~~~powershell
python -m forgeai evaluate --resume-generation --run .\artifacts\my-groq-academic
~~~

Run the two demos sequentially because they share the same account quotas.

Use --max-iterations 1 for a shorter baseline and optimization run. The default allows three iterations.

### NVIDIA Free Endpoint

Set NVIDIA_API_KEY in the same project-root .env, then select the model explicitly.
This uses a separate run folder and sends model payloads to NVIDIA.

~~~powershell
$brief = (Get-Content -Raw .\demo_data\procurement_brief.txt).Trim()
python -m forgeai build --non-interactive --max-iterations 1 --model nvidia:nvidia/nemotron-3.5-lightning-30b-a3b --brief $brief --docs .\demo_data\procurement --out .\artifacts\my-nvidia-procurement
~~~
