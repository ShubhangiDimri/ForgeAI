"""Replay a frozen dataset with pinned models and resumable provider checkpoints."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import time

import forgeai


def replay(source: Path, benchmark: Path, out: Path, overlay: Path | None) -> None:
    if overlay is None and (out / "runtime_snapshot").is_dir():
        overlay = out / "runtime_snapshot"
    if overlay:
        forgeai.__path__.insert(0, str(overlay.resolve()))
    from forgeai import evaluation, judge, retrieval, runner, workflow
    from forgeai.documents import digest
    from forgeai.evaluation import read_frozen
    from forgeai.llm import PROMPTS, Groq, make_model

    original = json.loads((source / "run_metadata.json").read_bytes())
    fingerprint = digest(benchmark.read_bytes())
    dataset = read_frozen(benchmark, fingerprint)
    modules = ("schema.py", "llm.py", "documents.py", "judge.py", "tools.py", "workflow.py")
    runtime = {name: digest((PROMPTS.parent / name).read_bytes()) for name in modules}
    runtime.update({Path(module.__file__).name: digest(Path(module.__file__).read_bytes())
                    for module in (evaluation, retrieval, runner)})
    provenance = {
        "source_run": source.name, "eval_sha256": fingerprint, "max_iterations": 0,
        "agent_model": original["agent_model"], "judge_model": original["judge_model"],
        "embedding": original["embedding"], "runtime_hashes": runtime,
        "prompt_hashes": {p.name: digest(p.read_bytes()) for p in sorted(PROMPTS.glob("*.txt"))},
    }
    meta_path, cases_path = out / "run_metadata.json", out / "case_results" / "v0.json"
    if meta_path.exists():
        metadata = json.loads(meta_path.read_bytes())
        if any(metadata.get(key) != value for key, value in provenance.items()):
            raise ValueError("Checkpoint provenance does not match the replay")
        if metadata["status"] == "complete":
            return
    else:
        out.mkdir(parents=True, exist_ok=True)
        for name in ("agent_config.json", "corpus.json", "sources.json"):
            shutil.copyfile(source / "versions" / "0" / name, out / name)
        for name in ("requirements.json", "coverage.json", "document_manifest.json"):
            shutil.copyfile(source / name, out / name)
        shutil.copyfile(benchmark, out / "eval_dataset.json")
        metadata = provenance | {"started": datetime.now(timezone.utc).isoformat(), "interruptions": []}
    read_frozen(out / "eval_dataset.json", fingerprint)
    agent = runner.Runner(out / "agent_config.json")
    evaluator = make_model(original["judge_model"])
    if not (isinstance(agent.model, Groq) and isinstance(evaluator, Groq)
            and agent.model.model == original["agent_model"] and evaluator.model == original["judge_model"]):
        raise ValueError("Replay requires the original pinned Groq models")
    results = workflow._load_results(cases_path) if cases_path.is_file() else []
    if [row.case for row in results] != list(dataset.cases[:len(results)]):
        raise ValueError("Saved traces differ from the frozen cases")
    metadata.update(status="running")
    workflow.write_json(meta_path, metadata)
    workflow.save_version(out / "versions" / "0", agent)
    start = time.monotonic()
    try:
        for case in dataset.cases[len(results):]:
            result = judge.assess(case, agent.trace(case.question), evaluator)
            if result.status == "error" and any(
                f"HTTP {status}" in result.explanation for status in (401, 403, 429, 500, 502, 503, 504)
            ):
                metadata["interruptions"].append({"case_id": case.id, "error": result.explanation,
                                                "time": datetime.now(timezone.utc).isoformat()})
                workflow.write_json(out / "provider_checkpoint.json", result.model_dump(mode="json"))
                raise RuntimeError(f"Provider interrupted {case.id}: {result.explanation}")
            results.append(result)
            workflow.write_json(cases_path, [row.model_dump(mode="json") for row in results])
            print(out.name, case.id, result.status, flush=True)
        card = workflow.score(results, 0, time.monotonic() - start + metadata.get("elapsed_seconds", 0))
        workflow.write_json(out / "scorecards.json", [card])
        workflow.write_json(out / "iteration_logs.json", [])
        workflow.report(out, [card], [], 0, "frozen replay finished", results, agent.config)
        metadata.update(status="complete_with_errors" if card["error"] else "complete", selected_version=0,
                        stop_reason="frozen replay finished")
    except (Exception, KeyboardInterrupt) as exc:
        metadata.update(status="incomplete", stop_reason=str(exc))
        raise
    finally:
        metadata["updated_at"] = datetime.now(timezone.utc).isoformat()
        metadata["elapsed_seconds"] = round(time.monotonic() - start + metadata.get("elapsed_seconds", 0), 2)
        workflow.write_json(meta_path, metadata)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--runtime-overlay", type=Path)
    args = parser.parse_args()
    replay(args.source, args.benchmark, args.out, args.runtime_overlay)
