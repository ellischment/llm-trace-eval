"""LLM call wrapped in an OpenTelemetry span. `mock` backend needs no API key."""
import time
from dataclasses import dataclass

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer("llm-trace-eval")


@dataclass
class LLMResult:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


def _call_anthropic(model: str, prompt: str, max_tokens: int) -> LLMResult:
    import anthropic  # reads ANTHROPIC_API_KEY from the environment

    resp = anthropic.Anthropic().messages.create(
        model=model, max_tokens=max_tokens, messages=[{"role": "user", "content": prompt}]
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    return LLMResult(text, resp.usage.input_tokens, resp.usage.output_tokens)


def _call_mock(model: str, prompt: str, max_tokens: int) -> LLMResult:
    # Deterministic stand-in: always answers "42", so the pipeline runs end to end without a key.
    return LLMResult("42", len(prompt.split()), 1)


BACKENDS = {"anthropic": _call_anthropic, "mock": _call_mock}


def call_llm(backend: str, model: str, prompt: str, max_tokens: int = 64) -> LLMResult:
    with tracer.start_as_current_span("llm.call") as span:
        span.set_attribute("llm.backend", backend)
        span.set_attribute("llm.model", model)
        span.set_attribute("llm.prompt", prompt)
        start = time.perf_counter()
        try:
            result = BACKENDS[backend](model, prompt, max_tokens)
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
        span.set_attribute("llm.latency_s", time.perf_counter() - start)
        span.set_attribute("llm.response", result.text)
        if result.input_tokens is not None:
            span.set_attribute("llm.usage.input_tokens", result.input_tokens)
            span.set_attribute("llm.usage.output_tokens", result.output_tokens)
        return result
