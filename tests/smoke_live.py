"""Manual acceptance check against an actual generated agent and Ollama."""
import argparse
import json
from pathlib import Path
from forgeai.runner import Runner


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    agent = Runner(args.config)
    checks = [
        ("supported", "What is the minimum attendance per taught module?", False),
        ("unsupported", "Who qualifies for a scholarship?", True),
        ("out_of_scope", "What is the capital of France?", True),
    ]
    records = []
    for label, question, expected in checks:
        record = dict(case=label, question=question, expected_refusal=expected)
        try:
            answer = agent.answer(question)
            record["response"] = answer.model_dump()
            record["passed"] = answer.refused == expected
            if label == "supported":
                record["passed"] &= ("75" in answer.answer and
                                     any(c.startswith("attendance.txt#") for c in answer.citations))
        except Exception as exc:
            record.update(error=str(exc), passed=False)
        records.append(record)
        print(json.dumps(record), flush=True)
        args.config.with_name("smoke.json").write_text(json.dumps(records, indent=2), encoding="utf8")
    return int(not all(r["passed"] for r in records))


if __name__ == "__main__":
    raise SystemExit(main())

