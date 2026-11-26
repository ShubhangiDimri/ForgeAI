"""Lightweight FastAPI wrapper around the existing ForgeAI pipeline."""
from __future__ import annotations

from copy import deepcopy
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
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from forgeai import generator as gen_mod
from forgeai import llm as llm_mod
from forgeai import runner as runner_mod
from forgeai import workflow as workflow_mod
from forgeai.schema import Finding, Requirements

BACKEND_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = BACKEND_ROOT / "artifacts"
DEMO_DATA_DIR = BACKEND_ROOT / "demo_data"
UPLOADS_DIR = BACKEND_ROOT / "uploads"

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".csv"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB per file

app = FastAPI(title="ForgeAI API", version="1.0.0")

# In-memory build job state (keyed by build_id)
_BUILDS_LOCK = threading.Lock()
_BUILDS: dict[str, dict[str, Any]] = {}
_RUNNERS_LOCK = threading.Lock()
_RECOVERIES: set[str] = set()
_RUNNERS: dict[tuple[str, str | None], tuple[tuple[int | None, ...], runner_mod.Runner]] = {}

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


def _get_runner(run_id: str, model: str | None) -> runner_mod.Runner:
    with _RUNNERS_LOCK:
        run_path = _run_dir(run_id)
        config_path = run_path / "agent_config.json"
        if not config_path.is_file():
            raise HTTPException(status_code=404, detail="Agent configuration not found")
        paths = (config_path, run_path / "corpus.json", run_path / "sources.json")
        revision = tuple(path.stat().st_mtime_ns if path.is_file() else None for path in paths)
        key = (run_id, model)
        cached = _RUNNERS.get(key)
        if cached is None or cached[0] != revision:
            _RUNNERS[key] = revision, runner_mod.Runner(config_path, model_override=model)
        return _RUNNERS[key][1]


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
    model: str | None = Field(default=None, max_length=160)


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


def _has_groq_key() -> bool:
    try:
        llm_mod.groq_key()
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
                "configured": _has_groq_key(),
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
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Enter a question.")
    if req.model and not any(
        provider["configured"] and req.model in provider["models"]
        for provider in providers()["providers"]
    ):
        raise HTTPException(status_code=422, detail="Choose an available chat model.")
    try:
        runner = _get_runner(run_id, req.model)
    except (OSError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"Could not load agent. {exc}") from exc
    trace = runner.trace(question)
    if trace.error:
        raise HTTPException(status_code=502, detail=trace.error)
    return trace.model_dump(mode="json") | {"model": runner.model.model}


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
        def checkpoint(status: str, data: dict[str, Any], reply: str) -> Any:
            with _BUILDS_LOCK:
                build = _BUILDS[build_id]
                event = build["_event"]
                event.clear()
                build.update(data, status=status)
            if not event.wait(timeout=1800):
                raise TimeoutError("Build checkpoint expired after 30 minutes")
            with _BUILDS_LOCK:
                build = _BUILDS[build_id]
                build["status"] = "running"
                return build[reply]

        def answer_questions(questions: list[str]) -> dict[str, str]:
            answers = checkpoint("waiting_intake", {"questions": questions}, "answers")
            return dict(zip(questions, answers))

        def approve(requirements: Requirements, coverage: dict[str, Finding]) -> Requirements:
            response = checkpoint("waiting_approval", {
                "requirements": requirements.model_dump(mode="json"),
                "coverage": {topic: finding.model_dump(mode="json") for topic, finding in coverage.items()},
            }, "approved_requirements")
            return Requirements.model_validate(response)

        stages = ("ingestion", "intake", "groundability", "generation")

        def progress(stage: str, status: str, detail: str) -> None:
            _set_stage(build_id, stages.index(stage), status, detail)

        embedding = os.getenv("FORGE_EMBEDDING", "sentence-transformers/all-MiniLM-L6-v2")
        gen_mod.build(
            req.brief, docs_path, out_dir, True, llm_mod.make_model(req.model), embedding,
            answer_questions=answer_questions if req.interactive else None,
            approve=approve if req.interactive else None, progress=progress,
        )

        if not req.prototype_only:
            _set_stage(build_id, 4, "running", "Generating and freezing evaluation cases")
            cards = workflow_mod.run(out_dir, req.judge_model, max_iterations=req.max_iterations)
            _set_stage(build_id, 4, "completed", f"{cards[0]['total']} cases frozen")
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
        return deepcopy({k: v for k, v in b.items() if k != "_event"})


@app.post("/api/builds/{build_id}/intake")
def submit_intake(build_id: str, req: IntakeAnswersRequest) -> dict[str, Any]:
    with _BUILDS_LOCK:
        b = _BUILDS.get(build_id)
        if not b:
            raise HTTPException(status_code=404, detail="Build not found")
        if b["status"] != "waiting_intake":
            raise HTTPException(status_code=409, detail="Build is not waiting for intake answers")
        b["answers"] = req.answers
        b["status"] = "running"
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
        b["status"] = "running"
        b["_event"].set()
    return {"status": "resumed"}


@app.post("/api/runs/{run_id}/resume")
def resume_run(run_id: str, req: ResumeRequest) -> dict[str, Any]:
    folder = _run_dir(run_id)
    metadata = _read_json_if_exists(folder / "run_metadata.json") or {}
    if metadata.get("status") != "incomplete":
        raise HTTPException(status_code=409, detail="Only incomplete runs can be resumed.")
    if req.mode == "scoring" and not (folder / "eval_dataset.json").is_file():
        raise HTTPException(status_code=409, detail="Scoring requires a frozen dataset.")
    if req.mode == "generation" and (
        (folder / "eval_dataset.json").is_file() or not (folder / "eval_generation_progress.json").is_file()
    ):
        raise HTTPException(status_code=409, detail="Generation resume requires saved drafts and no frozen dataset.")
    with _BUILDS_LOCK:
        if run_id in _RECOVERIES:
            raise HTTPException(status_code=409, detail="This run is already resuming.")
        _RECOVERIES.add(run_id)

    def worker() -> None:
        try:
            if req.mode == "scoring":
                workflow_mod.resume_scoring(folder, req.judge_model)
            else:
                workflow_mod.run(folder, req.judge_model, max_iterations=metadata.get("max_iterations", 3),
                                 resume_generation=True)
        except Exception as exc:
            current = _read_json_if_exists(folder / "run_metadata.json") or metadata
            if current.get("status") not in {"complete", "complete_with_errors"}:
                current.update(status="incomplete", stop_reason=f"{type(exc).__name__}: {exc}")
                workflow_mod.write_json(folder / "run_metadata.json", current)
        finally:
            with _BUILDS_LOCK:
                _RECOVERIES.discard(run_id)

    threading.Thread(target=worker, daemon=True).start()
    return {"run_id": run_id, "status": "resuming", "mode": req.mode}
