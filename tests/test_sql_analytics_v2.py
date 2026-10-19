"""Synthetic SQL semantics tests, never evidence of actual market movements."""

import hashlib
import pytest
from app.database import Store


@pytest.fixture
def market(tmp_path):
    store = Store(tmp_path / "market.sqlite3")
    store.execute("INSERT INTO sources(id,name,status) VALUES ('s','SYNTHETIC publisher','HEALTHY')")

    def add(identity, period, value, geo="City", definition="overall", status="APPROVED", unit="percent"):
        text = f"SYNTHETIC {geo} vacancy {period} = {value} {unit}."
        path = tmp_path / (identity + ".txt")
        path.write_text(text)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        store.execute(
            "INSERT INTO documents(id,source_id,text,raw_path,raw_hash,status,url,publisher) VALUES (?,'s',?,?,?,'SOURCE_VERIFIED',?,'SYNTHETIC publisher')",
            (identity, text, str(path), digest, "https://example.org/" + identity),
        )
        store.execute(
            "INSERT INTO observations(id,document_id,metric,geography,period,value,unit,definition,publisher,evidence_text,review_status) VALUES (?,?,'vacancy_rate',?,?,?,?,?,'SYNTHETIC publisher',?,?)",
            (identity, identity, geo, period, value, unit, definition, text, status),
        )

    return store, add


def test_sql_lag_computes_only_compatible_consecutive_quarters(market):
    from app.analytics.engine import Analytics, QuerySpec

    store, add = market
    add("a", "2026Q1", 6.8)
    add("b", "2026Q2", 6.7)
    add("c", "2026Q4", 6.1)
    result = Analytics(store).query(QuerySpec(metric="vacancy_rate", operation="trend"))
    a, b, c = result["rows"]
    assert a["comparison_status"] == "NO_PREVIOUS_PERIOD"
    assert b["absolute_change"] == pytest.approx(-0.1) and b["change_unit"] == "percentage points"
    assert c["comparison_status"] == "MISSING_PERIOD" and c["absolute_change"] is None


def test_pending_definitions_regions_and_sources_never_blend(market):
    from app.analytics.engine import Analytics, QuerySpec

    store, add = market
    add("a", "2026Q1", 6.8)
    add("b", "2026Q2", 6.7, status="PENDING_REVIEW")
    add("other-region", "2026Q2", 8, geo="West End")
    add("other-definition", "2026Q2", 2, definition="Grade A only")
    result = Analytics(store).query(QuerySpec(metric="vacancy_rate", operation="trend"))
    assert len(result["rows"]) == 3 and all(r["absolute_change"] is None for r in result["rows"])
    assert all(r["review_status"] == "APPROVED" for r in result["rows"])


def test_duplicate_conflicting_period_is_withheld_and_revision_does_not_bridge(market):
    from app.analytics.engine import Analytics, QuerySpec

    store, add = market
    add("a", "2026Q1", 6.8)
    add("b", "2026Q2", 6.7)
    add("conflict", "2026Q2", 7.1)
    result = Analytics(store).query(QuerySpec(metric="vacancy_rate", operation="trend"))
    assert not any(r["absolute_change"] is not None for r in result["rows"])
    assert result["conflicts"] and result["conflicts"][0]["period"] == "2026Q2"


def test_raw_integrity_and_revocation_withdraw_sql_evidence(market):
    from app.analytics.engine import Analytics, QuerySpec

    store, add = market
    add("a", "2026Q1", 6.8)
    add("b", "2026Q2", 6.7)
    engine = Analytics(store)
    assert len(engine.query(QuerySpec(metric="vacancy_rate"))["rows"]) == 2
    path = store.one("SELECT raw_path FROM documents WHERE id='b'")["raw_path"]
    from pathlib import Path

    Path(path).write_bytes(b"tampered")
    result = engine.query(QuerySpec(metric="vacancy_rate"))
    assert [r["id"] for r in result["rows"]] == ["a"] and result["integrity_failures"] == ["b"]
    store.execute("UPDATE observations SET review_status='RETRACTED' WHERE id='a'")
    assert not engine.query(QuerySpec(metric="vacancy_rate"))["rows"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"operation": "DROP TABLE sources"},
        {"metric": "vacancy_rate;DELETE"},
        {"limit": 999999},
        {"sql": "SELECT * FROM settings"},
    ],
)
def test_query_spec_rejects_raw_sql_and_unbounded_inputs(kwargs):
    from app.analytics.engine import QuerySpec
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        QuerySpec(**kwargs)


def test_parameterized_geo_does_not_change_sql_or_mutate(market):
    from app.analytics.engine import Analytics, QuerySpec

    store, add = market
    add("a", "2026Q1", 6.8)
    result = Analytics(store).query(QuerySpec(metric="vacancy_rate", geographies=["City' OR 1=1 --"]))
    assert result["rows"] == [] and store.one("SELECT count(*) n FROM observations")["n"] == 1


def test_year_over_year_requires_exact_four_quarter_lag(market):
    from app.analytics.engine import Analytics, QuerySpec

    store, add = market
    for i, value in enumerate([8, 7.7, 7.5, 7.2, 7]):
        add(str(i), f"{2025 + i // 4}Q{i % 4 + 1}", value)
    rows = Analytics(store).query(QuerySpec(metric="vacancy_rate", operation="compare", comparison="yoy"))[
        "rows"
    ]
    assert rows[-1]["absolute_change"] == -1 and rows[-1]["previous_period"] == "2025Q1"


def test_rolling_never_uses_pending_inputs(market):
    from app.analytics.engine import Analytics, QuerySpec

    store, add = market
    for i in range(4):
        add(str(i), f"2026Q{i + 1}", i + 1, status="APPROVED" if i == 3 else "PENDING_REVIEW")
    result = Analytics(store).query(QuerySpec(operation="rolling", review_status="ALL"))
    assert result["rows"][-1]["rolling_mean"] is None


def test_latest_is_latest_inside_selected_interval(market):
    from app.analytics.engine import Analytics, QuerySpec

    store, add = market
    for i in range(4):
        add(str(i), f"2026Q{i + 1}", i + 1)
    result = Analytics(store).query(QuerySpec(operation="latest", end_period="2026Q2"))
    assert [x["period"] for x in result["rows"]] == ["2026Q2"]


def test_month_filter_retains_quarter_inside_calendar_range(market):
    from app.analytics.engine import Analytics, QuerySpec

    store, add = market
    add("quarter", "2026Q2", 6.7)
    result = Analytics(store).query(QuerySpec(start_period="2025M09", end_period="2026M08"))
    assert [x["period"] for x in result["rows"]] == ["2026Q2"]
