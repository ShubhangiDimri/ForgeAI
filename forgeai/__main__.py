import argparse
import os
import sys
from pathlib import Path
from .generator import build
from .llm import GROQ_DEFAULT, make_model
from .runner import Runner


def main() -> int:
    parser = argparse.ArgumentParser(prog="forgeai")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("build")
    create.add_argument("--prototype-only", action="store_true")
    create.add_argument("--max-iterations", type=int, choices=range(4), default=3)
    create.add_argument("--judge-model", default=os.getenv("FORGE_JUDGE_MODEL"))
    create.add_argument("--brief", required=True)
    create.add_argument("--docs", required=True, type=Path)
    create.add_argument("--out", required=True, type=Path)
    create.add_argument("--non-interactive", action="store_true")
    create.add_argument("--model", help="Ollama tag, groq:<model-id>, or nvidia:<model-id>")
    create.add_argument("--groq", action="store_true", help="Use the default hosted Groq model")
    create.add_argument("--embedding", default=os.getenv("FORGE_EMBEDDING", "sentence-transformers/all-MiniLM-L6-v2"))
    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("--resume-generation", action="store_true")
    evaluate.add_argument("--resume-scoring", action="store_true",
                          help="Resume an interrupted evaluation from saved case results")
    evaluate.add_argument("--run", required=True, type=Path)
    evaluate.add_argument("--max-iterations", type=int, choices=range(4), default=3)
    evaluate.add_argument("--judge-model", default=os.getenv("FORGE_JUDGE_MODEL"))
    chat = commands.add_parser("chat")
    chat.add_argument("--config", required=True, type=Path)
    chat.add_argument("--question")
    args = parser.parse_args()
    try:
        if args.command == "build":
            model = args.model or (GROQ_DEFAULT if args.groq else os.getenv("FORGE_MODEL", "gemma2:2b"))
            build(args.brief, args.docs, args.out, args.non_interactive, make_model(model), args.embedding)
            print(args.out / "agent_config.json", flush=True)
            if not args.prototype_only:
                from .workflow import run
                run(args.out, args.judge_model, max_iterations=args.max_iterations)
        elif args.command == "evaluate":
            from .workflow import run, resume_scoring
            if args.resume_scoring:
                resume_scoring(args.run, args.judge_model)
            else:
                run(args.run, args.judge_model, max_iterations=args.max_iterations,
                    resume_generation=args.resume_generation)
        else:
            runner = Runner(args.config)
            if args.question:
                print(runner.answer(args.question).model_dump_json(indent=2))
            else:
                while True:
                    question = input("> ").strip()
                    if question in {"", "/quit"}:
                        break
                    try:
                        print(runner.answer(question).model_dump_json(indent=2))
                    except (ValueError, RuntimeError, ArithmeticError) as exc:
                        print(f"Question failed: {exc}", file=sys.stderr)
    except EOFError:
        return 0 if args.command == "chat" else 1
    except Exception as exc:
        print(f"ForgeAI error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

