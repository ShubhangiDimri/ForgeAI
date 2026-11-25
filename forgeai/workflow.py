"""Run the full factory and retain evidence for every measured configuration."""
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from pydantic import TypeAdapter

from .documents import digest
from .evaluation import freeze, generate, read_frozen
from .judge import Result, assess
from .llm import Ollama, PROMPTS
from .optimizer import changes, proposed_patch
from .runner import Runner
from .schema import Config, Passage

ITERATION_LIMIT = 3


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def save_version(folder: Path, runner: Runner) -> None:
    adapter = TypeAdapter(list[Passage])
    corpus = adapter.dump_json(runner.corpus)
    runner.config.corpus_sha256 = digest(corpus)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "corpus.json").write_bytes(corpus)
    if runner.sources is not None:
        snapshot = adapter.dump_json(runner.sources)
        runner.config.sources_sha256 = digest(snapshot)
        (folder / "sources.json").write_bytes(snapshot)
    write_json(folder / "agent_config.json", runner.config.model_dump(mode="json"))


def score(results: list[Result], version: int, seconds: float) -> dict:
    counts = {status: sum(r.status == status for r in results) for status in ("passed", "failed", "error")}
    dimensions = {}
    for result in results:
        if result.judgment:
            for dimension, value in result.judgment.model_dump().items():
                if isinstance(value, bool):
                    dimension_count = dimensions.setdefault(dimension, {"passed": 0, "scored": 0})
                    dimension_count["scored"] += 1
                    dimension_count["passed"] += int(value)
    return {"version": version, "total": len(results), **counts,
            "pass_rate": counts["passed"] / len(results), "dimensions": dimensions, "seconds": round(seconds, 2)}


def report(out: Path, cards: list[dict], logs: list[dict], best: int | None, stop: str,
           selected: list[Result], config: Config) -> None:
    lines = ["# ForgeAI quality report", "", f"- Stop reason · {stop}", f"- Selected version · {best}",
             f"- Agent model · {config.model}", f"- Embedding model · {config.embedding}", "",
             "| Version | Passed | Failed | Errors | Total | Rate | Seconds |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for card in cards:
        lines.append(f"| {card['version']} | {card['passed']} | {card['failed']} | {card['error']} | "
                     f"{card['total']} | {card['pass_rate']:.1%} | {card['seconds']} |")
    if best is not None:
        lines += ["", f"Measured improvement · {'yes' if cards[best]['pass_rate'] > cards[0]['pass_rate'] else 'no'}",
                  "", "## Selected version checks", ""]
        lines += [f"- {key} · {value['passed']}/{value['scored']} scored cases"
                  for key, value in cards[best]["dimensions"].items()]
        lines += ["", "## Remaining failures and errors", ""]
        lines += [f"- {r.case.id} · {r.failure or r.status} · {r.explanation}"
                  for r in selected if r.status != "passed"] or ["All cases in this run passed."]
    if logs:
        lines += ["", "## Targeted iterations", ""]
        lines += [f"- Version {log['iteration']} · {log['reason']} Outcome {log.get('outcome', 'unmeasured')}."
                  for log in logs]
    lines += ["", "## Assumptions and limitations", ""]
    lines += [f"- {s}" for s in [*config.requirements.assumptions, *config.requirements.unresolved]]
    lines += ["- Scores measure this frozen dataset only. The judge may share model biases with the agent.",
              "- Exact evidence checks establish provenance. Semantic relevance and unsupported-topic decisions depend on model judgments.",
              "- Ambiguous cases require a clarifying response, represented by the existing refusal flag.",
              "- Errors are counted in the denominator and excluded from semantic optimization.", ""]
    (out / "final_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(out: Path, judge_model: str | None = None, max_iterations: int = ITERATION_LIMIT) -> list[dict]:
    if not 0 <= max_iterations <= ITERATION_LIMIT:
        raise ValueError(f"Iterations must be between 0 and {ITERATION_LIMIT}")
    runner = Runner(out / "agent_config.json")
    if runner.sources is None:
        raise ValueError("Full evaluation requires a run with original source snapshots")
    generator = Ollama(runner.config.model)
    judge = Ollama(judge_model or runner.config.model)
    path = out / "eval_dataset.json"
    if path.exists() or (out / "run_metadata.json").exists():
        raise ValueError("Evaluation already started in this run directory")
    cards, logs, selected = [], [], []
    best = None
    metadata = {
        "status": "running", "started": datetime.now(timezone.utc).isoformat(),
        "agent_model": runner.config.model, "judge_model": judge.model,
        "embedding": runner.config.embedding, "max_iterations": max_iterations,
        "prompt_hashes": {p.name: digest(p.read_bytes()) for p in sorted(PROMPTS.glob("*.txt"))},
    }
    write_json(out / "run_metadata.json", metadata)
    stop = "evaluation did not finish"
    try:
        print("Generating evaluation cases", flush=True)
        fingerprint = freeze(generate(runner.config, runner.sources, generator,
            lambda cases: write_json(out / "eval_generation_progress.json", cases)), path)
        metadata["eval_sha256"] = fingerprint
        write_json(out / "run_metadata.json", metadata)
        for iteration in range(max_iterations + 1):
            dataset = read_frozen(path, fingerprint)
            save_version(out / "versions" / str(iteration), runner)
            results = []
            start = time.monotonic()
            result_path = out / "case_results" / f"v{iteration}.json"
            for case in dataset.cases:
                result = assess(case, runner.trace(case.question), judge)
                results.append(result)
                write_json(result_path, [item.model_dump(mode="json") for item in results])
                print(f"Version {iteration} {case.id} {result.status}", flush=True)
            current = score(results, iteration, time.monotonic() - start)
            cards.append(current)
            write_json(out / "scorecards.json", cards)
            if iteration:
                logs[-1]["after"] = current
                logs[-1]["outcome"] = ("improved" if current["pass_rate"] > logs[-1]["before"]["pass_rate"]
                                       else "no improvement")
                write_json(out / "iteration_logs.json", logs)
            if best is None or (current["passed"], -current["error"]) > (cards[best]["passed"], -cards[best]["error"]):
                best, selected = iteration, results
            if current["passed"] == current["total"]:
                stop = "all cases passed"
                break
            if current["error"] == current["total"]:
                stop = "all cases encountered execution or judge errors"
                break
            if iteration and best != iteration:
                # Roll back a non-improving change before considering another category.
                baseline = Config.model_validate_json((out / "versions" / str(best) / "agent_config.json").read_bytes())
                runner.reconfigure(baseline)
                results = selected
            if iteration == max_iterations:
                stop = "iteration budget reached"
                break
            patch = proposed_patch(runner.config, results, tuple(log["changes"] for log in logs))
            if patch is None:
                stop = "no actionable semantic patch"
                break
            candidate, why, affected = patch
            change = changes(runner.config, candidate)
            if any(log["changes"] == change for log in logs):
                stop = "next targeted patch already measured"
                break
            logs.append({"iteration": iteration + 1, "base_version": best, "changes": change,
                         "reason": why, "affected_case_ids": affected, "before": cards[best]})
            write_json(out / "iteration_logs.json", logs)
            runner.reconfigure(candidate)
        assert best is not None
        chosen = Config.model_validate_json((out / "versions" / str(best) / "agent_config.json").read_bytes())
        runner.reconfigure(chosen)
        save_version(out, runner)
        metadata["status"] = "complete" if not any(card["error"] for card in cards) else "complete_with_errors"
    except (Exception, KeyboardInterrupt) as exc:
        metadata["status"] = "incomplete"
        stop = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        metadata.update(stop_reason=stop, selected_version=best, finished=datetime.now(timezone.utc).isoformat())
        write_json(out / "run_metadata.json", metadata)
        write_json(out / "iteration_logs.json", logs)
        write_json(out / "scorecards.json", cards)
        report(out, cards, logs, best, stop, selected, runner.config)
    return cards

