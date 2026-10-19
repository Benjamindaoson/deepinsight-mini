"""Synthetic tool/transport tests; no provider or external notifications."""

import json
import subprocess
import sys
from app.database import Store


def test_eight_domain_skills_have_executable_schemas_and_documents(tmp_path):
    from app.tools.registry import registry, execute
    from pathlib import Path

    store = Store(tmp_path / "db.sqlite3")
    tools = registry()
    groups = {t.skill for t in tools.values()}
    assert len(groups) == 8
    for skill in groups:
        assert (Path("app/skills") / skill / "SKILL.md").is_file()
    for tool in tools.values():
        assert tool.input_schema.model_json_schema() and tool.output_schema.model_json_schema()
        assert tool.timeout > 0 and tool.description and tool.error_codes
    for name, args in [
        ("search_market_sources", {}),
        ("query_market_metrics", {}),
        ("get_data_coverage", {}),
        ("compare_submarkets", {"metric": "vacancy_rate"}),
        ("get_market_events", {}),
        ("get_monitor_status", {}),
        ("verify_report", {"report_id": "missing"}),
    ]:
        result = execute(store, name, args)
        assert result.tool_name == name and result.duration_ms >= 0 and isinstance(result.evidence_ids, list)


def test_tool_mutations_and_unknown_parameters_are_rejected(tmp_path):
    from app.tools.registry import execute

    store = Store(tmp_path / "db.sqlite3")
    for name, args in [
        ("run_market_monitor", {}),
        ("fetch_source_updates", {"source_id": "s"}),
        ("generate_market_briefing", {}),
    ]:
        result = execute(store, name, args)
        assert result.status == "ERROR" and result.data["error_code"] == "PERMISSION_REQUIRED"
    assert execute(store, "approve_observation", {}).data["error_code"] == "TOOL_NOT_REGISTERED"
    assert (
        execute(store, "query_market_metrics", {"sql": "DROP TABLE observations"}).data["error_code"]
        == "INVALID_INPUT"
    )
    assert store.one("SELECT count(*) n FROM monitor_runs")["n"] == 0


def test_document_and_metric_skills_execute_with_a_retained_original(tmp_path):
    import hashlib
    from app.tools.registry import execute

    store = Store(tmp_path / "db.sqlite3")
    # Synthetic extraction fixture, not a statement about actual market rent.
    text = "SYNTHETIC: the City prime rent stood at £125 per sq ft."
    original = tmp_path / "original.txt"
    original.write_text(text, encoding="utf-8")
    store.execute(
        "INSERT INTO sources(id,status,config) VALUES ('s','HEALTHY',?)",
        (json.dumps(dict(id="savills_q2_2026")),),
    )
    store.execute(
        "INSERT INTO documents(id,source_id,text,raw_path,raw_hash,status,publisher) VALUES ('d','s',?,?,?,'SOURCE_VERIFIED','SYNTHETIC')",
        (text, str(original), hashlib.sha256(original.read_bytes()).hexdigest()),
    )
    read = execute(store, "read_market_document", dict(document_id="d"))
    assert read.status == "SUCCESS" and read.data["text"] == text
    extracted = execute(
        store, "extract_market_metrics", dict(document_id="d"), permissions={"read", "collect"}
    )
    assert extracted.status == "SUCCESS" and extracted.data["candidates"] == 1
    observation = store.one("SELECT * FROM observations")
    assert observation["review_status"] == "PENDING_REVIEW"
    assert observation["unit"] == "GBP/sq ft"


def test_stdio_mcp_list_and_call_use_same_registry_without_model(tmp_path):
    import os

    environment = dict(os.environ, MINI_DATA_DIR=str(tmp_path), MINI_OUTPUT_DIR=str(tmp_path / "output"))
    requests = [
        dict(jsonrpc="2.0", id=1, method="initialize", params={}),
        dict(jsonrpc="2.0", id=2, method="tools/list", params={}),
        dict(jsonrpc="2.0", id=3, method="tools/call", params={"name": "get_data_coverage", "arguments": {}}),
    ]
    run = subprocess.run(
        [sys.executable, "-m", "app.tools.mcp_adapter"],
        input="\n".join(json.dumps(r) for r in requests) + "\n",
        text=True,
        capture_output=True,
        env=environment,
        timeout=15,
        check=True,
    )
    responses = [json.loads(line) for line in run.stdout.splitlines()]
    assert responses[0]["result"]["capabilities"]["tools"] == {}
    assert len(responses[1]["result"]["tools"]) >= 16
    assert responses[2]["result"]["structuredContent"]["tool_name"] == "get_data_coverage"
