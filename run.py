import argparse
import json
import sys

from llm_trace_eval.harness import run_eval
from llm_trace_eval.tracing import setup_tracing, shutdown


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--backend", choices=["mock", "anthropic"], default="mock")
    p.add_argument("--model", default="claude-haiku-5-5")
    p.add_argument("--dataset", default="data/eval50.jsonl")
    p.add_argument("--limit", type=int)
    p.add_argument("--out", default="results.json")
    args = p.parse_args()

    setup_tracing()
    try:
        result = run_eval(args.backend, args.model, args.dataset, args.limit)
    except FileNotFoundError as exc:
        sys.exit(f"error: {exc}")
    finally:
        shutdown()
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"{result['backend']}/{result['model']}: accuracy {result['accuracy']:.2%} on {result['n']} examples")


if __name__ == "__main__":
    main()
