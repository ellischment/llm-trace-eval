"""Tests for the answer check and the mock-mode eval loop.

Tracing is wired to an in-memory exporter once per session, so the eval
test can verify the span tree without touching traces.jsonl.
"""
import json
from pathlib import Path

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from llm_trace_eval.harness import is_correct, run_eval

DATASET = Path(__file__).resolve().parent.parent / "data" / "eval50.jsonl"


@pytest.fixture(scope="session")
def spans() -> InMemorySpanExporter:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return exporter


@pytest.mark.parametrize("response, gold", [
    ("Paris", "Paris"),
    ("paris.", "Paris"),
    ('"Paris"\n', "Paris"),
    ("Buenos  Aires", "Buenos Aires"),
    ("1,000", "1000"),
    ("-5", "-5"),
])
def test_is_correct_tolerates_case_punctuation_and_spacing(response, gold):
    assert is_correct(response, gold)


@pytest.mark.parametrize("response, gold", [
    ("Not Paris, Milan", "Paris"),
    ("The capital is Paris", "Paris"),
    ("-5", "5"),
    ("3.5", "35"),
    ("1000", "100"),
    ("", "42"),
])
def test_is_correct_rejects_partial_and_lookalike_answers(response, gold):
    assert not is_correct(response, gold)


def test_run_eval_mock_scores_every_example(spans):
    examples = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
    # The dataset deliberately contains "Compute 6 * 7", so the mock backend ("42") scores above zero
    # and a metric that returns all-False or all-True fails here.
    expected_correct = sum(is_correct("42", ex["answer"]) for ex in examples)
    assert 0 < expected_correct < len(examples)

    result = run_eval("mock", "any-model", str(DATASET))

    assert result["n"] == len(examples) == len(result["rows"])
    assert result["accuracy"] == pytest.approx(expected_correct / len(examples))
    assert sum(row["correct"] for row in result["rows"]) == expected_correct
    for row, ex in zip(result["rows"], examples):
        assert set(row) == {"id", "question", "gold", "response", "correct"}
        assert row["id"] == ex["id"] and row["gold"] == ex["answer"]
        assert row["correct"] == is_correct(row["response"], row["gold"])


def test_run_eval_emits_one_span_tree_per_run(spans):
    spans.clear()
    n = 7

    run_eval("mock", "any-model", str(DATASET), limit=n)

    by_name = {}
    for s in spans.get_finished_spans():
        by_name.setdefault(s.name, []).append(s)
    assert len(by_name["eval.run"]) == 1
    assert len(by_name["eval.example"]) == n
    assert len(by_name["llm.call"]) == n
    run_id = by_name["eval.run"][0].context.span_id
    example_ids = {s.context.span_id for s in by_name["eval.example"]}
    assert all(s.parent.span_id == run_id for s in by_name["eval.example"])
    assert all(s.parent.span_id in example_ids for s in by_name["llm.call"])
    for s in by_name["llm.call"]:
        assert {"llm.model", "llm.prompt", "llm.response", "llm.latency_s"} <= set(s.attributes)
        assert s.attributes["llm.latency_s"] >= 0


def test_run_eval_reports_missing_dataset(tmp_path):
    with pytest.raises(FileNotFoundError, match="dataset not found"):
        run_eval("mock", "any-model", str(tmp_path / "missing.jsonl"))
