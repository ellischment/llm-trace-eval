"""OpenTelemetry setup. Spans go to the console by default, or to an OTLP endpoint if configured."""
import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


def setup_tracing(service_name: str = "llm-trace-eval") -> trace.Tracer:
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        exporter = OTLPSpanExporter()
    else:
        exporter = ConsoleSpanExporter(out=open(os.getenv("TRACE_FILE", "traces.jsonl"), "w", encoding="utf-8"))
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)


def flush() -> None:
    provider = trace.get_tracer_provider()
    if hasattr(provider, "force_flush"):
        provider.force_flush()
