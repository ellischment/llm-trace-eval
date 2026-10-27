"""Eval loop: one parent span per run, one child span per example."""
import json
import re
from pathlib import Path

from opentelemetry import trace

from .client import call_llm

tracer = trace.get_tracer("llm-trace-eval")


def normalize(s: str) -> str:
    return re.sub(r"[^\w\s]", "", s).strip().lower()


def is_correct(response: str, gold: str) -> bool:
    return normalize(gold) in normalize(response).split() or normalize(response) == normalize(gold)


def load_examples(path: str) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def run_eval(backend: str, model: str, dataset: str, limit: int | None = None) -> dict:
    examples = load_examples(dataset)[:limit]
    rows = []
    with tracer.start_as_current_span("eval.run") as run_span:
        run_span.set_attribute("eval.dataset", dataset)
        run_span.set_attribute("eval.n", len(examples))
        for ex in examples:
            with tracer.start_as_current_span("eval.example") as span:
                span.set_attribute("eval.id", ex["id"])
                try:
                    res = call_llm(backend, model, ex["question"])
                    ok = is_correct(res.text, ex["answer"])
                    response = res.text
                except Exception as exc:  # a failed call counts as an incorrect example
                    ok, response = False, f"ERROR: {exc}"
                span.set_attribute("eval.correct", ok)
                rows.append({"id": ex["id"], "question": ex["question"], "gold": ex["answer"],
                             "response": response, "correct": ok})
        acc = sum(r["correct"] for r in rows) / max(len(rows), 1)
        run_span.set_attribute("eval.accuracy", acc)
    return {"backend": backend, "model": model, "n": len(rows), "accuracy": acc, "rows": rows}
