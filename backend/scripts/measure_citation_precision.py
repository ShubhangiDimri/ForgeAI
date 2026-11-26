"""Replay a frozen demo in a new folder with one answer-stage intervention."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import json
import shutil
import time

from forgeai.documents import digest
from forgeai.evaluation import read_frozen
from forgeai.judge import assess
from forgeai.llm import PROMPTS, Groq, make_model
from forgeai.runner import Runner
from forgeai.workflow import _load_results, report, save_version, score, write_json


def read_json(path):
    return json.loads(path.read_bytes())


def measure(source: Path, out: Path) -> None:
    source, out = source.resolve(), out.resolve()
    if out.is_relative_to(source) or source.is_relative_to(out):
        raise ValueError("Use a separate experiment folder")
    original = read_json(source / "run_metadata.json")
    fingerprint = original["eval_sha256"]
    dataset = read_frozen(source / "eval_dataset.json", fingerprint)
    tracked = ("schema.py", "runner.py", "llm.py", "evaluation.py", "judge.py",
               "retrieval.py", "documents.py", "tools.py", "workflow.py")
    metadata_path = out / "run_metadata.json"
    provenance = {
        "source_run": source.name,
        "eval_sha256": fingerprint,
        "agent_model": original["agent_model"],
        "judge_model": original["judge_model"],
        "max_iterations": 1,
        "prompt_hashes": {p.name: digest(p.read_bytes()) for p in sorted(PROMPTS.glob("*.txt"))},
        "runtime_hashes": {name: digest((PROMPTS.parent / name).read_bytes()) for name in tracked},
        "experiment_hash": digest(Path(__file__).read_bytes()),
    }
    if metadata_path.exists():
        meta = read_json(metadata_path)
        if any(meta.get(key) != value for key, value in provenance.items()):
            raise ValueError("Checkpoint provenance does not match current code, prompts and models")
        if meta["status"] == "complete":
            return
    else:
        out.mkdir(parents=True, exist_ok=False)
        for name in ("agent_config.json", "corpus.json", "sources.json"):
            shutil.copyfile(source / "versions" / "0" / name, out / name)
        shutil.copyfile(source / "eval_dataset.json", out / "eval_dataset.json")
        meta = provenance | {"started": datetime.now(timezone.utc).isoformat(), "interruptions": []}
    expected = {case.id: case for case in read_frozen(out / "eval_dataset.json", fingerprint).cases}
    runner = Runner(out / "agent_config.json")
    judge = make_model(original["judge_model"])
    if not isinstance(runner.model, Groq) or not isinstance(judge, Groq) or runner.model.model != original["agent_model"]:
        raise ValueError("The experiment requires the original pinned Groq models, without fallback")
    base = runner.config.model_copy(update={"precise_citations": False})
    # Each repetition below is under the same rubric. Historical cards are context only.
    cards, logs, results_by_version = [], [], []
    meta.update(status="running", selected_version=None)
    write_json(metadata_path, meta)
    try:
        for version in range(2):
            runner.reconfigure(base.model_copy(update={"precise_citations": bool(version)}))
            save_version(out / "versions" / str(version), runner)
            result_path = out / "case_results" / f"v{version}.json"
            results = _load_results(result_path) if result_path.exists() else []
            saved = {result.case.id for result in results}
            if len(saved) != len(results) or any(result.case != expected.get(result.case.id) for result in results):
                raise ValueError("Checkpoint case results do not match frozen cases")
            start = time.monotonic()
            for case in dataset.cases:
                if case.id in saved:
                    continue
                result = assess(case, runner.trace(case.question), judge)
                if result.status == "error" and any(
                    f"HTTP {status}" in result.explanation for status in (401, 403, 429, 500, 502, 503, 504)
                ):
                    meta["interruptions"].append({
                        "version": version, "case_id": case.id, "reason": result.explanation,
                        "recorded_at": datetime.now(timezone.utc).isoformat(),
                    })
                    write_json(out / "provider_checkpoint.json", {
                        "version": version, "case_id": case.id, "result": result.model_dump(mode="json"),
                    })
                    raise RuntimeError(f"Provider interruption at version {version} {case.id}: {result.explanation}")
                results.append(result)
                write_json(result_path, [item.model_dump(mode="json") for item in results])
                print(f"{source.name} v{version} {case.id} {result.status}", flush=True)
            previous = next((c for c in read_json(out / "scorecards.json") if c["version"] == version), None) if (out / "scorecards.json").is_file() else None
            cards.append(previous if previous and len(saved) == len(dataset.cases)
                         else score(results, version, time.monotonic() - start))
            results_by_version.append(results)
            if version:
                logs.append({"iteration": 1, "changes": {"precise_citations": {"before": False, "after": True}},
                             "reason": "Limit claims and citations to what the question requires.",
                             "before": cards[0], "after": cards[1],
                             "outcome": "improved" if cards[1]["passed"] > cards[0]["passed"] else "no pass-count improvement"})
            write_json(out / "scorecards.json", cards)
            write_json(out / "iteration_logs.json", logs)
        best = max(range(2), key=lambda i: (cards[i]["passed"], -cards[i]["error"], -i))
        runner.reconfigure(base.model_copy(update={"precise_citations": bool(best)}))
        save_version(out, runner)
        meta.update(status="complete", selected_version=best, stop_reason="One controlled optimization iteration measured")
        report(out, cards, logs, best, meta["stop_reason"], results_by_version[best], runner.config)
    except (Exception, KeyboardInterrupt) as exc:
        meta.update(status="incomplete", stop_reason=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        meta["updated_at"] = datetime.now(timezone.utc).isoformat()
        write_json(metadata_path, meta)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    measure(args.run, args.out)
