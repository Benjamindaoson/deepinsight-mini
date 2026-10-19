"""One permission-aware registry; no arbitrary SQL, shell or review mutation tool."""

from dataclasses import dataclass
import time
from pydantic import ValidationError
from app.analytics.engine import QuerySpec
from .contracts import Empty, DocumentInput, ReportInput, ToolResult


@dataclass(frozen=True)
class Tool:
    name: str
    skill: str
    description: str
    input_schema: type
    function: object
    permission: str = "read"
    timeout: int = 10
    output_schema: type = ToolResult
    evidence_requirements: str = "Existing source-bound evidence; quantitative publication requires approval."
    error_codes: tuple = ("INVALID_INPUT", "PERMISSION_REQUIRED", "EVIDENCE_UNAVAILABLE", "TOOL_FAILED")


def registry():
    from app.skills import (
        source_discovery as s1,
        document_intelligence as s2,
        metric_extraction as s3,
        sql_analytics as s4,
    )
    from app.skills import (
        submarket_analysis as s5,
        event_intelligence as s6,
        continuous_monitoring as s7,
        executive_reporting as s8,
    )

    rows = []

    def add(module, name, schema, description, permission="read", timeout=10):
        rows.append(
            Tool(
                name,
                module.__name__.rsplit(".", 1)[1],
                description,
                schema,
                getattr(module, name),
                permission,
                timeout,
            )
        )

    add(s1, "search_market_sources", s1.SearchInput, "Find registered primary sources and collection health.")
    add(
        s1,
        "search_document_evidence",
        s1.SearchInput,
        "Search retained original documents with FTS5 and return source IDs and exact excerpts.",
    )
    add(
        s1,
        "fetch_source_updates",
        s1.FetchInput,
        "Fetch one enabled source; explicit collection permission required.",
        "collect",
        120,
    )
    for name in ["read_market_document", "get_source_evidence"]:
        add(
            s2,
            name,
            DocumentInput,
            "Inspect retained original evidence, source URL, dates, hash and review status.",
        )
    add(
        s3,
        "extract_market_metrics",
        DocumentInput,
        "Extract pending candidates from a retained original; never approve.",
        "collect",
        30,
    )
    add(
        s3,
        "validate_market_observations",
        QuerySpec,
        "Check source-bound observation eligibility and definitions.",
    )
    for name in ["query_market_metrics", "compare_market_periods", "get_market_trends", "get_data_coverage"]:
        add(
            s4,
            name,
            QuerySpec,
            "Execute parameterized SQL analytics; incompatible periods and pending values do not support changes.",
        )
    for name in ["compare_submarkets", "analyse_submarket"]:
        add(
            s5,
            name,
            QuerySpec,
            "Analyze source-defined submarkets without merging incompatible areas or publishers.",
        )
    for name in ["get_market_events", "deduplicate_events"]:
        add(
            s6,
            name,
            s6.EventInput,
            "Read and deduplicate dated source-backed market events, separate from inferred impacts.",
        )
    for name in ["get_monitor_status", "get_verified_changes"]:
        add(s7, name, Empty, "Inspect persistent monitor state, next London slots and verified changes.")
    add(
        s7,
        "run_market_monitor",
        Empty,
        "Run the shared monitor only on an explicit user request.",
        "monitor",
        300,
    )
    add(
        s8,
        "generate_market_briefing",
        Empty,
        "Save a shared evidence-constrained briefing when explicitly requested.",
        "report",
        60,
    )
    add(
        s8,
        "verify_report",
        ReportInput,
        "Revalidate current report dependencies; do not infer semantic approval.",
    )
    add(
        s8,
        "export_report",
        s8.ExportInput,
        "Export an existing report using the common HTML/PDF renderer.",
        "report",
        120,
    )
    return {t.name: t for t in rows}


def native_tools():
    return [
        dict(
            type="function",
            function=dict(
                name=t.name, description=t.description, parameters=t.input_schema.model_json_schema()
            ),
        )
        for t in registry().values()
        if t.permission == "read"
    ]


def execute(store, name, arguments, permissions=frozenset({"read"})):
    started = time.perf_counter()
    tool = registry().get(name)
    status = "SUCCESS"
    data = {}
    ids = []
    warnings = []
    try:
        if not tool:
            raise ValueError("TOOL_NOT_REGISTERED")
        args = tool.input_schema.model_validate(arguments)
        if tool.permission not in permissions:
            raise ValueError("PERMISSION_REQUIRED")
        data = tool.function(store, args)
        ids = data.get("evidence_ids", [])
        warnings = data.get("warnings", []) or data.get("limitations", [])
        if data.get("status") in ["SUCCESS", "PARTIAL", "INSUFFICIENT_EVIDENCE", "NOT_COMPARABLE"]:
            status = data["status"]
    except ValidationError:
        status = "ERROR"
        data = dict(error_code="INVALID_INPUT")
    except ValueError as exc:
        status = "ERROR"
        data = dict(error_code=str(exc) if str(exc).isupper() else "EVIDENCE_UNAVAILABLE")
    except Exception as exc:
        status = "ERROR"
        data = dict(error_code="TOOL_FAILED", error_type=type(exc).__name__)
    return ToolResult(
        tool_name=name,
        status=status,
        data=data,
        evidence_ids=ids,
        warnings=warnings,
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
    )
