"""Lightweight FastAPI wrapper around the existing ForgeAI pipeline."""
from __future__ import annotations

from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import re
import threading
import time
import uuid
import zipfile
from typing import Any, Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from forgeai import coverage as cov_mod
from forgeai import documents as docs_mod
from forgeai import generator as gen_mod
from forgeai import intake as intake_mod
from forgeai import llm as llm_mod
from forgeai import runner as runner_mod
from forgeai import workflow as workflow_mod
from forgeai.schema import Config, Questions, Requirements

BACKEND_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = BACKEND_ROOT / "artifacts"
DEMO_DATA_DIR = BACKEND_ROOT / "demo_data"
UPLOADS_DIR = BACKEND_ROOT / "uploads"

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".csv"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB per file

app = FastAPI(title="ForgeAI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory build job state (keyed by build_id)
_BUILDS_LOCK = threading.Lock()
_BUILDS: dict[str, dict[str, Any]] = {}
_RUNNERS_LOCK = threading.Lock()
_RUNNERS: dict[str, runner_mod.Runner] = {}

PIPELINE_STAGES = [
    "Document ingestion",
    "Intake interview",
    "Groundability verification",
    "Agent generation",
    "Evaluation generation",
    "Baseline evaluation",
    "Critic and optimization",
    "Final reporting",
]


def _safe_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", value):
        raise HTTPException(status_code=400, detail="Invalid identifier")
    return value


def _run_dir(run_id: str) -> Path:
    safe = _safe_id(run_id)
    target = (ARTIFACTS_DIR / safe).resolve()
    if target.parent != ARTIFACTS_DIR.resolve() or not target.is_dir():
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return target


def _read_json_if_exists(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _get_runner(run_id: str) -> runner_mod.Runner:
    with _RUNNERS_LOCK:
        if run_id not in _RUNNERS:
            run_path = _run_dir(run_id)
            config_path = run_path / "agent_config.json"
            if not config_path.is_file():
                raise HTTPException(status_code=404, detail="Agent configuration not found")
            _RUNNERS[run_id] = runner_mod.Runner(config_path)
        return _RUNNERS[run_id]


# ---------------------------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------------------------

class BuildRequest(BaseModel):
    name: str = Field(default="", max_length=60)
    brief: str = Field(min_length=10, max_length=4000)
    upload_id: str | None = None
    demo_dataset: str | None = None
    model: str = Field(default=llm_mod.GROQ_DEFAULT)
    judge_model: str | None = None
    max_iterations: int = Field(default=1, ge=0, le=3)
    interactive: bool = False
    prototype_only: bool = False


class IntakeAnswersRequest(BaseModel):
    answers: list[str] = Field(max_length=5)


class ApproveRequirementsRequest(BaseModel):
    requirements: Requirements


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class ResumeRequest(BaseModel):
    mode: Literal["scoring", "generation"] = "scoring"
    judge_model: str | None = None


# ---------------------------------------------------------------------------
# Health & Providers
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "artifacts_dir": str(ARTIFACTS_DIR.name),
    }


def _has_key(var: str) -> bool:
    try:
        llm_mod.provider_key(var)
        return True
    except RuntimeError:
        return False


@app.get("/api/providers")
def providers() -> dict[str, Any]:
    return {
        "providers": [
            {
                "id": "groq",
                "name": "Groq",
                "configured": _has_key("GROQ_API_KEY") or _has_key("GROQ_API_KEY_1") or _has_key("GROQ_API_KEY_2"),
                "default_model": llm_mod.GROQ_DEFAULT,
                "judge_model": llm_mod.GROQ_JUDGE,
                "models": ["groq:openai/gpt-oss-120b", "groq:openai/gpt-oss-20b"],
            },
            {
                "id": "nvidia",
                "name": "NVIDIA NIM",
                "configured": _has_key("NVIDIA_API_KEY"),
                "default_model": "nvidia:nvidia/nemotron-3.5-lightning-30b-a3b",
                "models": ["nvidia:nvidia/nemotron-3.5-lightning-30b-a3b"],
            },
            {
                "id": "cloudflare",
                "name": "Cloudflare Workers AI",
                "configured": _has_key("CLOUDFLARE_API_TOKEN") and _has_key("CLOUDFLARE_ACCOUNT_ID"),
                "default_model": "cloudflare:@cf/meta/llama-3.3-70b-instruct-fp8-fast",
                "models": ["cloudflare:@cf/meta/llama-3.3-70b-instruct-fp8-fast"],
            },
            {
                "id": "ollama",
                "name": "Ollama (Local)",
                "configured": True,
                "default_model": os.getenv("FORGE_MODEL", "gemma2:2b"),
                "models": ["gemma2:2b", "qwen2.5:3b"],
            },
        ],
        "fallback_order": llm_mod._fallback_chain(),
        "default_embedding": os.getenv("FORGE_EMBEDDING", "sentence-transformers/all-MiniLM-L6-v2"),
    }


@app.get("/api/examples")
def examples() -> dict[str, Any]:
    items = []
    if DEMO_DATA_DIR.is_dir():
        for brief_file in sorted(DEMO_DATA_DIR.glob("*brief*.txt")):
            items.append({
                "id": brief_file.stem,
                "label": brief_file.stem.replace("_", " ").title(),
                "brief": brief_file.read_text(encoding="utf-8").strip(),
            })
    datasets = []
    if DEMO_DATA_DIR.is_dir():
        for sub in sorted(DEMO_DATA_DIR.iterdir()):
            if sub.is_dir():
                datasets.append({
                    "id": sub.name,
                    "files": [f.name for f in sorted(sub.iterdir()) if f.is_file()],
                })
    return {"briefs": items, "datasets": datasets}


# ---------------------------------------------------------------------------
# Runs & Artifacts
# ---------------------------------------------------------------------------

@app.get("/api/runs")
def list_runs() -> dict[str, Any]:
    runs = []
    if ARTIFACTS_DIR.is_dir():
        for folder in sorted(ARTIFACTS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if not folder.is_dir():
                continue
            cfg = _read_json_if_exists(folder / "agent_config.json")
            if not cfg:
                continue
            meta = _read_json_if_exists(folder / "run_metadata.json") or {}
            cards = _read_json_if_exists(folder / "scorecards.json") or []
            selected_idx = meta.get("selected_version")
            selected_card = None
            if isinstance(cards, list) and cards:
                if isinstance(selected_idx, int) and 0 <= selected_idx < len(cards):
                    selected_card = cards[selected_idx]
                else:
                    selected_card = cards[0]
            runs.append({
                "id": folder.name,
                "scope": cfg.get("requirements", {}).get("scope", folder.name),
                "model": cfg.get("model", ""),
                "status": meta.get("status", "prototype" if not cards else "unknown"),
                "created_at": meta.get("started") or datetime.fromtimestamp(folder.stat().st_mtime, timezone.utc).isoformat(),
                "finished_at": meta.get("finished"),
                "selected_version": selected_idx,
                "baseline_pass_rate": cards[0]["pass_rate"] if cards else None,
                "selected_pass_rate": selected_card["pass_rate"] if selected_card else None,
                "total_cases": selected_card["total"] if selected_card else None,
                "tools": [t["name"] for t in cfg.get("tools", [])],
            })
    return {"runs": runs}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    folder = _run_dir(run_id)
    config = _read_json_if_exists(folder / "agent_config.json")
    if not config:
        raise HTTPException(status_code=404, detail="Agent configuration not found")
    case_results = {}
    cr_dir = folder / "case_results"
    if cr_dir.is_dir():
        for f in sorted(cr_dir.glob("v*.json")):
            case_results[f.stem] = _read_json_if_exists(f) or []
    report_path = folder / "final_report.md"
    final_report = report_path.read_text(encoding="utf-8") if report_path.is_file() else None
    files = [
        {"name": f.name, "size": f.stat().st_size}
        for f in sorted(folder.iterdir())
        if f.is_file()
    ]
    return {
        "id": run_id,
        "agent_config": config,
        "requirements": _read_json_if_exists(folder / "requirements.json"),
        "coverage": _read_json_if_exists(folder / "coverage.json"),
        "document_manifest": _read_json_if_exists(folder / "document_manifest.json"),
        "run_metadata": _read_json_if_exists(folder / "run_metadata.json"),
        "eval_dataset": _read_json_if_exists(folder / "eval_dataset.json"),
        "scorecards": _read_json_if_exists(folder / "scorecards.json") or [],
        "iteration_logs": _read_json_if_exists(folder / "iteration_logs.json") or [],
        "case_results": case_results,
        "final_report": final_report,
        "files": files,
    }


@app.get("/api/runs/{run_id}/artifacts/{filename}")
def download_artifact(run_id: str, filename: str):
    folder = _run_dir(run_id)
    safe_name = _safe_id(filename)
    target = (folder / safe_name).resolve()
    if target.parent != folder.resolve() or not target.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(target, filename=safe_name)


@app.get("/api/runs/{run_id}/download-zip")
def download_zip(run_id: str):
    folder = _run_dir(run_id)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=str(path.relative_to(folder)))
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{run_id}-artifacts.zip"'},
    )


# ---------------------------------------------------------------------------
# Playground Chat
# ---------------------------------------------------------------------------

@app.post("/api/runs/{run_id}/chat")
def chat(run_id: str, req: ChatRequest) -> dict[str, Any]:
    runner = _get_runner(run_id)
    trace = runner.trace(req.question.strip())
    if trace.error and trace.answer is None and not trace.invalid_citation and not trace.invalid_tool_call:
        raise HTTPException(status_code=502, detail=trace.error)
    return trace.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Document Uploads & Builds
# ---------------------------------------------------------------------------

@app.post("/api/uploads")
async def upload_documents(files: list[UploadFile] = File(...)) -> dict[str, Any]:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    upload_id = f"up-{uuid.uuid4().hex[:10]}"
    dest_dir = UPLOADS_DIR / upload_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for upload in files:
        raw_name = Path(upload.filename or "").name
        if not raw_name:
            raise HTTPException(status_code=400, detail="Invalid filename")
        ext = Path(raw_name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'. Allowed: PDF, TXT, CSV")
        content = await upload.read()
        if not content:
            raise HTTPException(status_code=400, detail=f"File '{raw_name}' is empty")
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=400, detail=f"File '{raw_name}' exceeds 10 MB limit")
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", raw_name)
        (dest_dir / safe_name).write_bytes(content)
        saved.append({"name": safe_name, "size": len(content)})
    return {"upload_id": upload_id, "files": saved}


def _init_stages() -> list[dict[str, Any]]:
    return [{"name": name, "status": "pending", "detail": ""} for name in PIPELINE_STAGES]


def _set_stage(build_id: str, index: int, status: str, detail: str = "") -> None:
    with _BUILDS_LOCK:
        b = _BUILDS[build_id]
        b["stages"][index]["status"] = status
        if detail:
            b["stages"][index]["detail"] = detail
        b["current_stage"] = PIPELINE_STAGES[index]


def _execute_build(build_id: str, req: BuildRequest, docs_path: Path, out_dir: Path) -> None:
    start_ts = time.monotonic()
    try:
        model = llm_mod.make_model(req.model)
        embedding = os.getenv("FORGE_EMBEDDING", "sentence-transformers/all-MiniLM-L6-v2")

        # 1. Document ingestion
        _set_stage(build_id, 0, "running", f"Reading {docs_path.name}")
        sources, manifest = docs_mod.load_folder(docs_path)
        _set_stage(build_id, 0, "completed", f"Loaded {len(manifest)} files ({len(sources)} passages)")

        # 2. Intake interview
        _set_stage(build_id, 1, "running", "Analyzing brief and excerpts")
        excerpts = intake_mod.sample_excerpts(sources)
        if req.interactive:
            q_resp = model.ask("questions", {"brief": req.brief, "documents": excerpts}, Questions)
            questions = q_resp.questions[:5]
            if questions:
                with _BUILDS_LOCK:
                    _BUILDS[build_id]["status"] = "waiting_intake"
                    _BUILDS[build_id]["questions"] = questions
                    _BUILDS[build_id]["_event"].clear()
                _BUILDS[build_id]["_event"].wait(timeout=1800)
                with _BUILDS_LOCK:
                    answers_list = _BUILDS[build_id].get("answers", [])
                    _BUILDS[build_id]["status"] = "running"
                qa = list(zip(questions, answers_list))
            else:
                qa = []
            requirements = intake_mod.gather(req.brief, sources, model, interactive=False) if not qa else model.ask(
                "requirements",
                {"brief": req.brief, "documents": excerpts, "answers": [{"question": q, "answer": a} for q, a in qa]},
                Requirements,
            )
        else:
            requirements = intake_mod.gather(req.brief, sources, model, interactive=False)
        _set_stage(build_id, 1, "completed", f"Scope: {requirements.scope[:80]}")

        # 3. Groundability verification
        _set_stage(build_id, 2, "running", "Checking topic groundability")
        findings = cov_mod.assess(requirements, sources, model, embedding)
        _set_stage(build_id, 2, "completed", f"Checked {len(findings)} topics")

        if req.interactive:
            with _BUILDS_LOCK:
                _BUILDS[build_id]["status"] = "waiting_approval"
                _BUILDS[build_id]["requirements"] = requirements.model_dump(mode="json")
                _BUILDS[build_id]["coverage"] = {k: v.model_dump(mode="json") for k, v in findings.items()}
                _BUILDS[build_id]["_event"].clear()
            _BUILDS[build_id]["_event"].wait(timeout=1800)
            with _BUILDS_LOCK:
                approved = _BUILDS[build_id].get("approved_requirements")
                if approved:
                    requirements = Requirements.model_validate(approved)
                _BUILDS[build_id]["status"] = "running"

        # 4. Agent generation
        _set_stage(build_id, 3, "running", "Generating validated agent definition")
        from forgeai.schema import Design, Passage, Answer
        from pydantic import TypeAdapter
        design = model.ask(
            "design",
            {
                "requirements": requirements.model_dump(),
                "coverage": {t: f.model_dump() for t, f in findings.items()},
                "tools": sorted(gen_mod.REGISTRY),
            },
            Design,
        )
        chunks = docs_mod.chunk(sources, design.settings)
        corpus_bytes = TypeAdapter(list[Passage]).dump_json(chunks)
        sources_bytes = TypeAdapter(list[Passage]).dump_json(sources)
        config = Config(
            **design.model_dump(),
            version=1,
            model=model.model,
            embedding=embedding,
            requirements=requirements,
            coverage=findings,
            document_manifest=manifest,
            output_contract=Answer.model_json_schema(),
            corpus_sha256=docs_mod.digest(corpus_bytes),
            sources_sha256=docs_mod.digest(sources_bytes),
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "requirements.json").write_text(requirements.model_dump_json(indent=2), encoding="utf-8")
        (out_dir / "coverage.json").write_text(
            json.dumps({k: v.model_dump() for k, v in findings.items()}, indent=2), encoding="utf-8"
        )
        (out_dir / "document_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        (out_dir / "corpus.json").write_bytes(corpus_bytes)
        (out_dir / "sources.json").write_bytes(sources_bytes)
        (out_dir / "agent_config.json").write_text(config.model_dump_json(indent=2), encoding="utf-8")
        _set_stage(build_id, 3, "completed", f"Saved {out_dir.name}")

        if not req.prototype_only:
            _set_stage(build_id, 4, "running", "Generating and freezing evaluation cases")
            workflow_mod.run(out_dir, req.judge_model, max_iterations=req.max_iterations)
            _set_stage(build_id, 4, "completed", "20 cases frozen")
            _set_stage(build_id, 5, "completed", "Baseline scored")
            _set_stage(build_id, 6, "completed", "Optimization complete")
            _set_stage(build_id, 7, "completed", "Final report written")
        else:
            for idx in range(4, 8):
                _set_stage(build_id, idx, "completed", "Skipped (prototype-only)")

        with _BUILDS_LOCK:
            _BUILDS[build_id]["status"] = "completed"
            _BUILDS[build_id]["elapsed_seconds"] = round(time.monotonic() - start_ts, 2)
    except Exception as exc:
        with _BUILDS_LOCK:
            b = _BUILDS[build_id]
            b["status"] = "failed"
            b["error"] = f"{type(exc).__name__}: {exc}"
            b["elapsed_seconds"] = round(time.monotonic() - start_ts, 2)
            for s in b["stages"]:
                if s["status"] == "running":
                    s["status"] = "failed"
                    s["detail"] = str(exc)[:200]


@app.post("/api/builds")
def start_build(req: BuildRequest) -> dict[str, Any]:
    if req.upload_id:
        docs_path = (UPLOADS_DIR / _safe_id(req.upload_id)).resolve()
        if not docs_path.is_dir():
            raise HTTPException(status_code=404, detail="Uploaded document folder not found")
    elif req.demo_dataset:
        docs_path = (DEMO_DATA_DIR / _safe_id(req.demo_dataset)).resolve()
        if not docs_path.is_dir():
            raise HTTPException(status_code=404, detail="Demo dataset not found")
    else:
        raise HTTPException(status_code=400, detail="Provide either upload_id or demo_dataset")

    slug = re.sub(r"[^a-z0-9-]+", "-", req.name.lower()).strip("-") or "agent"
    run_id = f"{slug}-{uuid.uuid4().hex[:6]}"
    out_dir = ARTIFACTS_DIR / run_id
    build_id = uuid.uuid4().hex[:10]
    with _BUILDS_LOCK:
        _BUILDS[build_id] = {
            "build_id": build_id,
            "run_id": run_id,
            "status": "running",
            "current_stage": PIPELINE_STAGES[0],
            "model": req.model,
            "stages": _init_stages(),
            "questions": [],
            "answers": [],
            "requirements": None,
            "coverage": None,
            "error": None,
            "elapsed_seconds": 0.0,
            "_event": threading.Event(),
        }
    t = threading.Thread(target=_execute_build, args=(build_id, req, docs_path, out_dir), daemon=True)
    t.start()
    return {"build_id": build_id, "run_id": run_id, "status": "running"}


@app.get("/api/builds/{build_id}")
def get_build(build_id: str) -> dict[str, Any]:
    with _BUILDS_LOCK:
        b = _BUILDS.get(build_id)
        if not b:
            raise HTTPException(status_code=404, detail="Build not found")
        return {k: v for k, v in b.items() if k != "_event"}


@app.post("/api/builds/{build_id}/intake")
def submit_intake(build_id: str, req: IntakeAnswersRequest) -> dict[str, Any]:
    with _BUILDS_LOCK:
        b = _BUILDS.get(build_id)
        if not b:
            raise HTTPException(status_code=404, detail="Build not found")
        if b["status"] != "waiting_intake":
            raise HTTPException(status_code=409, detail="Build is not waiting for intake answers")
        b["answers"] = req.answers
        b["_event"].set()
    return {"status": "resumed"}


@app.post("/api/builds/{build_id}/approve")
def approve_requirements(build_id: str, req: ApproveRequirementsRequest) -> dict[str, Any]:
    with _BUILDS_LOCK:
        b = _BUILDS.get(build_id)
        if not b:
            raise HTTPException(status_code=404, detail="Build not found")
        if b["status"] != "waiting_approval":
            raise HTTPException(status_code=409, detail="Build is not waiting for requirements approval")
        b["approved_requirements"] = req.requirements.model_dump(mode="json")
        b["_event"].set()
    return {"status": "resumed"}


@app.post("/api/runs/{run_id}/resume")
def resume_run(run_id: str, req: ResumeRequest) -> dict[str, Any]:
    folder = _run_dir(run_id)
    def _worker():
        if req.mode == "scoring":
            workflow_mod.resume_scoring(folder, req.judge_model)
        else:
            workflow_mod.run(folder, req.judge_model, resume_generation=True)
    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return {"run_id": run_id, "status": "resuming", "mode": req.mode}

