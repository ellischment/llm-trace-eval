"""OpenTelemetry setup. Spans go to a JSONL file by default, or to an OTLP endpoint if configured."""
import os
from typing import IO

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

_trace_file: IO[str] | None = None


def _one_span_per_line(span) -> str:
    # ConsoleSpanExporter pretty-prints by default; traces.jsonl must hold one span per line.
    return span.to_json(indent=None) + "\n"


def setup_tracing(service_name: str = "llm-trace-eval") -> trace.Tracer:
    global _trace_file
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        exporter = OTLPSpanExporter()
    else:
        _trace_file = open(os.getenv("TRACE_FILE", "traces.jsonl"), "w", encoding="utf-8")
        exporter = ConsoleSpanExporter(out=_trace_file, formatter=_one_span_per_line)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)


def flush() -> None:
    provider = trace.get_tracer_provider()
    if hasattr(provider, "force_flush"):
        provider.force_flush()


def shutdown() -> None:
    """Flush pending spans, stop the exporter and close the trace file."""
    global _trace_file
    flush()
    provider = trace.get_tracer_provider()
    if hasattr(provider, "shutdown"):
        provider.shutdown()
    if _trace_file is not None:
        _trace_file.close()
        _trace_file = None
