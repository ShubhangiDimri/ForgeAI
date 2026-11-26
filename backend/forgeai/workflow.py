"""Run the full factory and retain evidence for every measured configuration."""
from datetime import datetime, timezone
import json
import re
from collections.abc import Callable
from pathlib import Path
import time
from collections import Counter
from pydantic import TypeAdapter

from .documents import digest
from .evaluation import Case, freeze, generate, read_frozen
from .judge import Result, assess
from .llm import GROQ_JUDGE, PROMPTS, make_model
from .optimizer import changes, proposed_patch
from .runner import Runner
from .schema import Config, Passage

ITERATION_LIMIT = 3


def scoring_code_hashes() -> dict[str, str]:
    files = ("judge.py", "runner.py", "retrieval.py", "tools.py", "optimizer.py")
    return {name: digest(Path(__file__).with_name(name).read_bytes()) for name in files}


def pause_on_provider_error(result: Result) -> None:
    if result.status == "error" and re.search(
        r"HTTP (?:401|403|429|500|502|503|504)\b|provider offline|connection failed|timed out|providers exhausted",
        result.explanation, re.I,
    ):
        raise RuntimeError(f"Provider interrupted {result.case.id}: {result.explanation}")


def pin_model(client):
    return client._chain[0] if hasattr(client, "_chain") else client


def record_groq_slots(metadata: dict, **clients) -> None:
    used = metadata.setdefault("groq_key_slots_used", {})
    for stage, client in clients.items():
        slots = getattr(client, "credential_slots_used", None)
        if isinstance(slots, set) and slots:
            used[stage] = sorted(set(used.get(stage, [])) | slots)


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
             f"- Agent model · {config.model}", f"- Embedding model · {config.embedding}",
             "- [Agent definition](agent_config.json) · [Scorecards](scorecards.json) · [Iteration logs](iteration_logs.json)", "",
             "| Version | Passed | Failed | Errors | Total | Rate | Seconds |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for card in cards:
        lines.append(f"| {card['version']} | {card['passed']} | {card['failed']} | {card['error']} | "
                     f"{card['total']} | {card['pass_rate']:.1%} | {card['seconds']} |")
    if best is not None:
        lines += ["", f"Measured improvement · {'yes' if cards[best]['pass_rate'] > cards[0]['pass_rate'] else 'no'}",
                  "", "## Selected version checks", ""]
        lines += [f"- {key} · {value['passed']}/{value['scored']} scored cases"
                  for key, value in cards[best]["dimensions"].items()]
        outcomes = Counter(r.execution.answer.outcome for r in selected if r.execution.answer and r.execution.answer.outcome)
        if outcomes:
            lines += ["", "## Response outcomes", ""]
            lines += [f"- {outcome.replace('_', ' ').capitalize()} · {count}" for outcome, count in sorted(outcomes.items())]
        lines += ["", "## Remaining failures and errors", ""]
        lines += [f"- {r.case.id} · {r.failure or r.status} · {r.explanation}"
                  for r in selected if r.status != "passed"] or ["All cases in this run passed."]
    if logs:
        lines += ["", "## Targeted iterations", ""]
        for log in logs:
            fields = ", ".join(log["changes"])
            affected = ", ".join(log["affected_case_ids"])
            before, after = log.get("before"), log.get("after")
            comparison = (f"{before['passed']}/{before['total']} → {after['passed']}/{after['total']}"
                          if before and after else "awaiting a completed measurement")
            lines.append(f"- Version {log['iteration']} · {fields}. {log['reason']} Cases {affected}. {comparison}.")
    limitations = [(topic, finding) for topic, finding in config.coverage.items()
                   if finding.status != "supported" or finding.inconclusive]
    if limitations:
        lines += ["", "## Requirements with limited support", ""]
        for topic, finding in limitations:
            state = "inconclusive" if finding.inconclusive else finding.status
            lines.append(f"- {topic} ({state}) · {finding.limitation or 'No further detail recorded.'}")
    lines += ["", "## Assumptions and limitations", ""]
    lines += [f"- {s}" for s in [*config.requirements.assumptions, *config.requirements.unresolved]]
    lines += ["- Scores measure this frozen dataset only. The judge may share model biases with the agent.",
              "- Exact evidence checks establish provenance. Semantic relevance and unsupported-topic decisions depend on model judgments.",
              "- Ambiguous cases require a focused clarification.",
              "- Errors are counted in the denominator and excluded from semantic optimization.", ""]
    (out / "final_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(out: Path, judge_model: str | None = None, max_iterations: int = ITERATION_LIMIT,
        *, resume_generation: bool = False,
        progress: Callable[[int, str, str], None] | None = None) -> list[dict]:
    if not 0 <= max_iterations <= ITERATION_LIMIT:
        raise ValueError(f"Iterations must be between 0 and {ITERATION_LIMIT}")
    runner = Runner(out / "agent_config.json")
    if runner.sources is None:
        raise ValueError("Full evaluation requires a run with original source snapshots")
    runner.model = pin_model(runner.model)
    generator = make_model(runner.model.model)
    default_judge = GROQ_JUDGE if runner.config.model.startswith("groq:") else runner.config.model
    judge = pin_model(make_model(judge_model or default_judge))
    path = out / "eval_dataset.json"
    metadata_path = out / "run_metadata.json"
    draft_path = out / "eval_generation_progress.json"
    prompt_hashes = {p.name: digest(p.read_bytes()) for p in sorted(PROMPTS.glob("*.txt"))}
    resume_options = {}
    if resume_generation:
        if path.exists() or not metadata_path.is_file() or not draft_path.is_file():
            raise ValueError("Resume requires an incomplete run with saved drafts and no frozen dataset")
        previous = json.loads(metadata_path.read_bytes())
        prior_judge = previous.get("judge_model")
        if prior_judge and judge_model and judge.model != prior_judge:
            raise ValueError("Resume requires the original judge model")
        if prior_judge and not judge_model and judge.model != prior_judge:
            judge = pin_model(make_model(prior_judge))
        if (previous["status"] != "incomplete" or previous["agent_model"] != runner.model.model
                or any(prompt_hashes.get(name) != fingerprint
                        for name, fingerprint in previous["prompt_hashes"].items()
                        if name.startswith("eval_") or name == "boundary.txt")):
            raise ValueError("Resume requires the original agent model and unchanged prompts")
        resume_options["resume"] = TypeAdapter(tuple[Case, ...]).validate_json(draft_path.read_bytes())
        history = out / "generation_resume_history.json"
        attempts = json.loads(history.read_bytes()) if history.is_file() else []
        write_json(history, [*attempts, previous])
    elif path.exists() or metadata_path.exists():
        raise ValueError("Evaluation already started in this run directory")
    cards, logs, selected = [], [], []
    best = None
    metadata = {
        "status": "running", "started": datetime.now(timezone.utc).isoformat(),
        "agent_model": runner.model.model, "judge_model": judge.model,
        "evaluation_validator_model": judge.model,
        "ambiguity_draft_model": judge.model,
        "requested_model": runner.config.requested_model or runner.config.model,
        "generation_models": runner.config.generation_models,
        "embedding": runner.config.embedding, "max_iterations": max_iterations,
        "prompt_hashes": prompt_hashes,
        "scoring_code_hashes": scoring_code_hashes(),
        "resumed_drafts": len(resume_options.get("resume", ())),
    }
    write_json(out / "run_metadata.json", metadata)
    stop = "evaluation did not finish"
    try:
        if not draft_path.exists():
            write_json(draft_path, [])
        print("Generating evaluation cases", flush=True)
        fingerprint = freeze(generate(runner.config, runner.sources, generator,
            lambda cases: write_json(draft_path, cases), reviewer=judge, **resume_options), path)
        metadata["eval_sha256"] = fingerprint
        write_json(out / "run_metadata.json", metadata)
        if progress:
            progress(4, "completed", "Evaluation dataset frozen")
        for iteration in range(max_iterations + 1):
            dataset = read_frozen(path, fingerprint)
            save_version(out / "versions" / str(iteration), runner)
            results = []
            start = time.monotonic()
            result_path = out / "case_results" / f"v{iteration}.json"
            for case in dataset.cases:
                if progress:
                    progress(5 if iteration == 0 else 6, "running", f"Waiting for model · v{iteration} · {len(results) + 1}/{len(dataset.cases)}")
                result = assess(case, runner.trace(case.question, **({"history": list(case.history)} if case.history else {})), judge)
                pause_on_provider_error(result)
                results.append(result)
                write_json(result_path, [item.model_dump(mode="json") for item in results])
                print(f"Version {iteration} {case.id} {result.status}", flush=True)
            current = score(results, iteration, time.monotonic() - start)
            if current["error"] == current["total"]:
                raise RuntimeError(f"Version {iteration} has no semantic judgments. Resume scoring after investigating the errors.")
            cards.append(current)
            if progress and iteration == 0:
                progress(5, "completed", "Baseline scored")
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
        if progress:
            progress(6, "completed" if len(cards) > 1 else "skipped", "Optimization finished")
            progress(7, "running", "Writing quality report")
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
        record_groq_slots(metadata, generator=generator, agent=runner.model, judge=judge)
        metadata.update(stop_reason=stop, selected_version=best, finished=datetime.now(timezone.utc).isoformat())
        write_json(out / "run_metadata.json", metadata)
        write_json(out / "iteration_logs.json", logs)
        write_json(out / "scorecards.json", cards)
        report(out, cards, logs, best, stop, selected, runner.config)
    return cards


def _load_results(path: Path) -> list[Result]:
    """Load saved case results, stripping computed fields that cannot be re-parsed."""
    raw = json.loads(path.read_bytes())
    for item in raw:
        item.pop("score", None)  # computed_field; re-derived automatically
    return TypeAdapter(list[Result]).validate_python(raw)


def resume_scoring(out: Path, judge_model: str | None = None, *,
                   progress: Callable[[int, str, str], None] | None = None) -> list[dict]:
    """Resume an interrupted evaluation run, re-scoring only incomplete iterations.

    This function:
    - Reads the frozen dataset, existing scorecards, iteration logs and version
      configs that were saved before the interruption.
    - Resumes any incomplete scoring iteration from the last saved case result.
    - Runs remaining iterations up to the original max_iterations budget.
    - Updates scorecards, logs and report in place.
    - Never re-generates evaluation cases or changes models mid-run.
    """
    path = out / "eval_dataset.json"
    metadata_path = out / "run_metadata.json"
    scorecards_path = out / "scorecards.json"
    logs_path = out / "iteration_logs.json"

    if not path.is_file():
        raise ValueError("Resume requires a frozen eval_dataset.json in the run directory")
    if not metadata_path.is_file():
        raise ValueError("Resume requires an existing run_metadata.json")

    previous_meta = json.loads(metadata_path.read_bytes())
    if previous_meta.get("status") not in {"incomplete", "running"}:
        raise ValueError(f"Run already has status={previous_meta.get('status')}. Nothing to resume.")

    fingerprint = previous_meta.get("eval_sha256")
    if not fingerprint:
        raise ValueError("run_metadata.json does not contain eval_sha256; cannot verify dataset integrity")

    max_iterations = previous_meta.get("max_iterations", ITERATION_LIMIT)
    if not 0 <= max_iterations <= ITERATION_LIMIT:
        raise ValueError(f"Iterations must be between 0 and {ITERATION_LIMIT}")
    agent_model = previous_meta["agent_model"]
    runner = Runner(out / "agent_config.json")
    if runner.sources is None:
        raise ValueError("Full evaluation requires original source snapshots (sources.json)")

    # Determine judge model - preserve the original to ensure comparable results
    original_judge = previous_meta.get("judge_model", agent_model)
    if (out / "case_results").is_dir() and any((out / "case_results").glob("v*.json")):
        recorded = previous_meta.get("prompt_hashes", {})
        runtime = previous_meta.get("scoring_code_hashes")
        if runtime and runtime != scoring_code_hashes():
            raise ValueError("Scoring code changed after this run started. Run a fresh baseline before comparing.")
        scoring_prompts = {"boundary.txt", "route.txt", "resolve_question.txt", "answer.txt", "answer_precise.txt", "calculate.txt", "judge.txt"}
        if any(name in recorded and digest((PROMPTS / name).read_bytes()) != recorded[name] for name in scoring_prompts):
            raise ValueError("Scoring prompts changed after this run started. Run a fresh baseline before comparing.")
    if judge_model and judge_model != original_judge:
        raise ValueError("Resume requires the original judge model")
    runner.model = pin_model(runner.model)
    if runner.model.model != agent_model:
        raise ValueError("Resume requires the original agent model")
    judge = pin_model(make_model(original_judge))
    print(f"Resuming with agent={agent_model} judge={judge.model}", flush=True)

    # Load existing scorecards and iteration logs
    cards: list[dict] = json.loads(scorecards_path.read_bytes()) if scorecards_path.is_file() else []
    logs: list[dict] = json.loads(logs_path.read_bytes()) if logs_path.is_file() else []

    # Determine how many iterations have fully completed scorecards
    completed_versions = len(cards)
    # Find the highest version for which a complete or partial case results file exists
    case_results_dir = out / "case_results"

    dataset = read_frozen(path, fingerprint)

    # Restore the best version's runner config
    best: int | None = None
    selected: list[Result] = []
    for i, card in enumerate(cards):
        if best is None or (card["passed"], -card["error"]) > (cards[best]["passed"], -cards[best]["error"]):
            best = i
            version_config_path = out / "versions" / str(i) / "agent_config.json"
            if version_config_path.is_file():
                cfg = Config.model_validate_json(version_config_path.read_bytes())
                runner.reconfigure(cfg)
            # Load the results for the best version
            best_results_path = case_results_dir / f"v{i}.json"
            if best_results_path.is_file():
                selected = _load_results(best_results_path)

    # Restore most-recent iteration's config to continue from there
    if logs:
        last_log = logs[-1]
        # Check if the last iteration was completed
        if "after" not in last_log:
            # Last iteration was not completed; restore its config
            version_num = last_log["iteration"]
            version_path = out / "versions" / str(version_num) / "agent_config.json"
            if version_path.is_file():
                cfg = Config.model_validate_json(version_path.read_bytes())
                runner.reconfigure(cfg)
            else:
                # Apply the logged patch to reconstruct
                from .optimizer import proposed_patch as _pp
                # Can't reconstruct; use base version
                base_v = last_log.get("base_version", 0)
                base_path = out / "versions" / str(base_v) / "agent_config.json"
                if base_path.is_file():
                    cfg = Config.model_validate_json(base_path.read_bytes())
                    runner.reconfigure(cfg)

    metadata = {**previous_meta, "status": "running",
                "resumed_at": datetime.now(timezone.utc).isoformat(),
                "judge_model_resumed": judge.model}
    write_json(metadata_path, metadata)
    stop = "evaluation did not finish"

    try:
        for iteration in range(max_iterations + 1):
            result_path = case_results_dir / f"v{iteration}.json"

            if iteration < completed_versions:
                # Already have a full scorecard for this version; load results for best tracking
                if result_path.is_file():
                    iter_results = _load_results(result_path)
                    if best is None or (cards[iteration]["passed"], -cards[iteration]["error"]) > (cards[best]["passed"], -cards[best]["error"]):
                        best, selected = iteration, iter_results
                # Restore config for this version
                version_config = out / "versions" / str(iteration) / "agent_config.json"
                if version_config.is_file():
                    cfg = Config.model_validate_json(version_config.read_bytes())
                    runner.reconfigure(cfg)
                continue

            # Resume or start this iteration's scoring
            existing_results: list[Result] = []
            existing_ids: set[str] = set()
            start_time = time.monotonic()

            if result_path.is_file():
                # Partial results saved; resume from where we left off
                existing_results = _load_results(result_path)
                errored = [row for row in existing_results if row.status == "error"]
                if errored:
                    history_path = out / "scoring_retry_history" / f"v{iteration}.json"
                    history = json.loads(history_path.read_bytes()) if history_path.is_file() else []
                    write_json(history_path, [*history, [row.model_dump(mode="json") for row in errored]])
                    existing_results = [row for row in existing_results if row.status != "error"]
                existing_ids = {r.case.id for r in existing_results}
                elapsed = previous_meta.get("scoring_recovery", {}).get("elapsed_seconds", 0)
                start_time -= elapsed  # rough accounting
                print(f"Resuming v{iteration} from {len(existing_results)} saved cases", flush=True)
            else:
                # Save the version config snapshot
                save_version(out / "versions" / str(iteration), runner)

            results = list(existing_results)
            start = time.monotonic()
            for case in dataset.cases:
                if case.id in existing_ids:
                    continue
                if progress:
                    progress(5 if iteration == 0 else 6, "running", f"Scoring v{iteration} · {len(results) + 1}/{len(dataset.cases)}")
                result = assess(case, runner.trace(case.question, **({"history": list(case.history)} if case.history else {})), judge)
                pause_on_provider_error(result)
                results.append(result)
                write_json(result_path, [item.model_dump(mode="json") for item in results])
                print(f"Version {iteration} {case.id} {result.status}", flush=True)

            current = score(results, iteration, time.monotonic() - start)
            if current["error"] == current["total"]:
                raise RuntimeError(f"Version {iteration} still has no semantic judgments")
            if progress and iteration == 0:
                progress(5, "completed", "Baseline scored")
            if iteration < len(cards):
                cards[iteration] = current
            else:
                cards.append(current)
            write_json(scorecards_path, cards)

            if iteration:
                logs[-1]["after"] = current
                logs[-1]["outcome"] = ("improved" if current["pass_rate"] > logs[-1]["before"]["pass_rate"]
                                       else "no improvement")
                write_json(logs_path, logs)

            if best is None or (current["passed"], -current["error"]) > (cards[best]["passed"], -cards[best]["error"]):
                best, selected = iteration, results

            if current["passed"] == current["total"]:
                stop = "all cases passed"
                break
            if iteration and best != iteration:
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
            # Only append a new log if this iteration isn't already logged
            existing_log_iters = {log["iteration"] for log in logs}
            if (iteration + 1) not in existing_log_iters:
                logs.append({"iteration": iteration + 1, "base_version": best, "changes": change,
                             "reason": why, "affected_case_ids": affected, "before": cards[best]})
                write_json(logs_path, logs)
            runner.reconfigure(candidate)

        if progress:
            progress(6, "completed" if len(cards) > 1 else "skipped", "Optimization finished")
            progress(7, "running", "Writing quality report")
        assert best is not None
        chosen = Config.model_validate_json((out / "versions" / str(best) / "agent_config.json").read_bytes())
        runner.reconfigure(chosen)
        save_version(out, runner)
        metadata["status"] = "complete" if not any(card.get("error", 0) for card in cards) else "complete_with_errors"
    except (Exception, KeyboardInterrupt) as exc:
        metadata["status"] = "incomplete"
        stop = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        record_groq_slots(metadata, agent=runner.model, judge=judge)
        metadata.update(stop_reason=stop, selected_version=best, finished=datetime.now(timezone.utc).isoformat())
        write_json(metadata_path, metadata)
        write_json(logs_path, logs)
        write_json(scorecards_path, cards)
        report(out, cards, logs, best, stop, selected, runner.config)
    return cards

