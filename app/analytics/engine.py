"""Compile validated analytical requests to bounded, read-only SQLite queries."""

import hashlib
import json
import re
import sqlite3
import time
import calendar
from datetime import date
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

METRICS = (
    "prime_rent",
    "grade_a_rent",
    "vacancy_rate",
    "availability",
    "take_up",
    "leasing_transactions",
    "supply",
    "development_completions",
    "construction_pipeline",
    "prelet_share",
    "grade_a_take_up_share",
    "breeam_take_up_share",
    "active_demand",
    "bank_rate",
    "cpi_inflation",
    "employment_rate",
    "gdp_growth",
)


def period_bounds(value):
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value or ""):
        return (value, value)
    match = re.fullmatch(r"(\d{4})(?:([MQH])(\d+))?", value or "")
    if not match:
        return ("", "")
    year, frequency, part = int(match[1]), match[2], int(match[3] or 1)
    start_month = (
        part
        if frequency == "M"
        else (part - 1) * 3 + 1
        if frequency == "Q"
        else (part - 1) * 6 + 1
        if frequency == "H"
        else 1
    )
    end_month = (
        start_month
        if frequency == "M"
        else start_month + 2
        if frequency == "Q"
        else start_month + 5
        if frequency == "H"
        else 12
    )
    return (
        date(year, start_month, 1).isoformat(),
        date(year, end_month, calendar.monthrange(year, end_month)[1]).isoformat(),
    )


class QuerySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metric: Literal[*METRICS] | None = None
    geographies: list[str] = Field(default_factory=list, max_length=20)
    source_id: str | None = Field(default=None, max_length=100)
    grade: Literal["all", "prime", "grade_a"] = "all"
    operation: Literal["latest", "trend", "compare", "rolling", "rank", "coverage", "conflicts"] = "trend"
    comparison: Literal["qoq", "yoy"] = "qoq"
    review_status: Literal["APPROVED", "PENDING_REVIEW", "ALL"] = "APPROVED"
    start_period: str | None = None
    end_period: str | None = None
    limit: int = Field(default=240, ge=1, le=240)

    @field_validator("start_period", "end_period")
    @classmethod
    def period(cls, value):
        if value is not None and not re.fullmatch(r"20\d{2}(?:Q[1-4]|H[12]|M(?:0[1-9]|1[0-2]))?", value):
            raise ValueError("Use an explicit year, quarter, half-year or month")
        return value


SCHEMA = """
CREATE TABLE IF NOT EXISTS geographies(id TEXT PRIMARY KEY,canonical_name TEXT,parent_geography TEXT,definition_notes TEXT,boundary_source TEXT);
CREATE TABLE IF NOT EXISTS metric_definitions(id TEXT PRIMARY KEY,display_name TEXT,semantic_config TEXT);
CREATE TABLE IF NOT EXISTS source_series(id TEXT PRIMARY KEY,source_id TEXT,metric TEXT,geography TEXT,definition TEXT,unit TEXT,frequency TEXT);
CREATE TABLE IF NOT EXISTS observation_reviews(id TEXT PRIMARY KEY,observation_id TEXT,reviewer TEXT,decision TEXT,reason TEXT,reviewed_at TEXT);
CREATE TABLE IF NOT EXISTS event_sources(event_id TEXT,document_id TEXT,PRIMARY KEY(event_id,document_id));
CREATE INDEX IF NOT EXISTS obs_analytics ON observations(review_status,metric,geography,period,definition,publisher,unit);
CREATE VIEW IF NOT EXISTS document_versions AS SELECT id,source_id,url,version,previous_id,raw_hash,fetched_at FROM documents;
CREATE VIEW IF NOT EXISTS monitor_signals AS SELECT * FROM signals;
CREATE VIEW IF NOT EXISTS notification_outbox AS SELECT * FROM notifications;
CREATE VIEW IF NOT EXISTS v_market_events AS SELECT e.*,d.url,d.publisher FROM events e JOIN documents d ON d.id=e.document_id WHERE e.status='SOURCE_VERIFIED' AND d.status='SOURCE_VERIFIED';
CREATE VIEW IF NOT EXISTS v_latest_monitor_results AS SELECT * FROM monitor_runs ORDER BY started_at DESC;
CREATE VIEW IF NOT EXISTS v_observation_evidence AS
 SELECT o.*,d.source_id,d.url,d.title,d.published_at,d.fetched_at,d.raw_path,d.raw_hash,
        d.status document_status,s.status source_health,
        CASE WHEN substr(o.period,5,1) IN ('Q','H','M') THEN substr(o.period,5,1) ELSE 'Y' END frequency,
        CASE WHEN o.period GLOB '[0-9][0-9][0-9][0-9]Q[1-4]' THEN CAST(substr(o.period,1,4) AS INTEGER)*4+CAST(substr(o.period,6) AS INTEGER)
             WHEN o.period GLOB '[0-9][0-9][0-9][0-9]M[0-1][0-9]' AND CAST(substr(o.period,6) AS INTEGER) BETWEEN 1 AND 12 THEN CAST(substr(o.period,1,4) AS INTEGER)*12+CAST(substr(o.period,6) AS INTEGER)
             WHEN o.period GLOB '[0-9][0-9][0-9][0-9]H[1-2]' THEN CAST(substr(o.period,1,4) AS INTEGER)*2+CAST(substr(o.period,6) AS INTEGER)
             WHEN length(o.period)=4 AND o.period GLOB '[0-9][0-9][0-9][0-9]' THEN CAST(o.period AS INTEGER)
             ELSE NULL END period_index
 FROM observations o JOIN documents d ON d.id=o.document_id JOIN sources s ON s.id=d.source_id
 WHERE d.status='SOURCE_VERIFIED' AND s.status='HEALTHY'
   AND length(trim(COALESCE(o.evidence_text,'')))>0 AND instr(d.text,o.evidence_text)>0
   AND o.value IS NOT NULL AND abs(o.value)<1e20 AND o.review_status NOT IN ('REJECTED','RETRACTED');
CREATE VIEW IF NOT EXISTS v_approved_observations AS SELECT * FROM v_observation_evidence WHERE review_status='APPROVED';
CREATE VIEW IF NOT EXISTS v_latest_market_metrics AS
 SELECT * FROM (SELECT *,ROW_NUMBER() OVER(PARTITION BY metric,geography,definition,publisher,unit,source_id,frequency ORDER BY period DESC,fetched_at DESC,id) latest_rank FROM v_approved_observations) WHERE latest_rank=1;
CREATE VIEW IF NOT EXISTS v_market_data_coverage AS SELECT geography,metric,review_status,count(*) observation_count,max(period) latest_period FROM v_observation_evidence GROUP BY geography,metric,review_status;
CREATE VIEW IF NOT EXISTS v_submarket_trends AS SELECT *,LAG(value) OVER(PARTITION BY metric,geography,definition,publisher,unit,source_id,frequency ORDER BY period) previous_value FROM v_approved_observations;
CREATE VIEW IF NOT EXISTS v_comparable_period_changes AS
 WITH history AS (SELECT *,LAG(value) OVER(PARTITION BY metric,geography,definition,publisher,unit,source_id,frequency ORDER BY period) previous,
 LAG(period_index) OVER(PARTITION BY metric,geography,definition,publisher,unit,source_id,frequency ORDER BY period) previous_index
 FROM v_approved_observations)
 SELECT *,ROUND(value-previous,8) absolute_change,
 CASE WHEN previous!=0 THEN ROUND((value-previous)*100.0/previous,8) END relative_change_pct
 FROM history WHERE period_index-previous_index=1;
CREATE TRIGGER IF NOT EXISTS analytics_review_audit AFTER UPDATE OF review_status ON observations
 WHEN NEW.review_status!=OLD.review_status BEGIN
 INSERT INTO observation_reviews VALUES(lower(hex(randomblob(16))),NEW.id,NEW.reviewer,NEW.review_status,NEW.review_reason,NEW.reviewed_at);
 END;
"""


class Analytics:
    def __init__(self, store):
        self.store = store
        with store.connection() as conn:
            conn.executescript(SCHEMA)
            for metric in METRICS:
                conn.execute(
                    "INSERT OR IGNORE INTO metric_definitions VALUES (?,?,?)",
                    (
                        metric,
                        metric.replace("_", " ").title(),
                        json.dumps(
                            dict(
                                aggregation="no_unweighted_average",
                                approved_required=True,
                                comparison=[
                                    "publisher",
                                    "definition",
                                    "unit",
                                    "geography",
                                    "source_series",
                                    "frequency",
                                ],
                                display_precision="source precision retained; computed deltas labelled separately",
                            )
                        ),
                    ),
                )
            series = conn.execute(
                "SELECT DISTINCT source_id,metric,geography,definition,unit,frequency FROM v_observation_evidence"
            ).fetchall()
            for row in series:
                values = tuple(row)
                identity = hashlib.sha256(json.dumps(values).encode()).hexdigest()
                conn.execute(
                    "INSERT OR IGNORE INTO source_series VALUES (?,?,?,?,?,?,?)", (identity, *values)
                )
            conn.execute(
                "INSERT OR IGNORE INTO event_sources SELECT id,document_id FROM events WHERE document_id IS NOT NULL"
            )
            for geo in [
                "City",
                "West End",
                "Canary Wharf",
                "Midtown",
                "Fringe",
                "City Fringe",
                "Central London",
                "UK",
            ]:
                conn.execute(
                    "INSERT OR IGNORE INTO geographies VALUES (?,?,?,?,?)",
                    (
                        geo,
                        geo,
                        None,
                        "Publisher boundaries retained. No equivalence to overlapping or combined submarkets is assumed.",
                        None,
                    ),
                )

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.store.path.resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        conn.create_function("period_start", 1, lambda p: period_bounds(p)[0], deterministic=True)
        conn.create_function("period_end", 1, lambda p: period_bounds(p)[1], deterministic=True)
        deadline = time.monotonic() + 2
        conn.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        try:
            yield conn
        finally:
            conn.close()

    def query(self, spec):
        spec = QuerySpec.model_validate(spec) if not isinstance(spec, QuerySpec) else spec
        clauses = ["1=1"]
        params = []
        if spec.review_status != "ALL":
            clauses += ["review_status=?"]
            params += [spec.review_status]
        if spec.metric:
            clauses += ["metric=?"]
            params += [spec.metric]
        if spec.geographies:
            clauses += ["geography IN (" + ",".join("?" for _ in spec.geographies) + ")"]
            params += spec.geographies
        if spec.source_id:
            clauses += ["source_id=?"]
            params += [spec.source_id]
        if spec.grade != "all":
            clauses += ["metric=?"]
            params += ["prime_rent" if spec.grade == "prime" else "grade_a_rent"]
        # A review flag cannot establish an unstated rent time denominator.
        clauses += [
            "(review_status!='APPROVED' OR metric NOT IN ('prime_rent','grade_a_rent') OR unit NOT LIKE '%year%' OR lower(evidence_text) LIKE '%per annum%' OR lower(evidence_text) LIKE '%p.a.%' OR lower(evidence_text) LIKE '%per year%')"
        ]
        where = " AND ".join(clauses)
        with self._connection() as conn:
            originals = conn.execute(
                "SELECT DISTINCT document_id,raw_path,raw_hash FROM v_observation_evidence WHERE " + where,
                params,
            ).fetchall()
            good = []
            bad = []
            for doc in originals:
                try:
                    path = Path(doc["raw_path"] or "")
                    valid = (
                        path.is_file()
                        and path.stat().st_size <= 20_000_000
                        and hashlib.sha256(path.read_bytes()).hexdigest() == doc["raw_hash"]
                    )
                except (OSError, TypeError):
                    valid = False
                (good if valid else bad).append(doc["document_id"])
            if not good:
                return dict(
                    rows=[],
                    conflicts=[],
                    integrity_failures=bad,
                    evidence_ids=[],
                    status="INSUFFICIENT_EVIDENCE",
                    query=spec.model_dump(),
                )
            where += " AND document_id IN (" + ",".join("?" for _ in good) + ")"
            params += good
            key = "metric,geography,definition,publisher,unit,source_id,frequency"
            cte = f"""WITH scoped AS (SELECT * FROM v_observation_evidence WHERE {where}),
                conflicts AS (SELECT {key},period FROM scoped GROUP BY {key},period HAVING count(DISTINCT value)>1),
                dedup AS (SELECT *,ROW_NUMBER() OVER(PARTITION BY {key},period ORDER BY fetched_at DESC,id) duplicate_rank,
                    count(*) OVER(PARTITION BY {key},period) disclosures FROM scoped),
                eligible AS (SELECT d.* FROM dedup d WHERE duplicate_rank=1 AND NOT EXISTS
                    (SELECT 1 FROM conflicts c WHERE c.metric=d.metric AND c.geography=d.geography AND c.definition=d.definition
                     AND c.publisher=d.publisher AND c.unit=d.unit AND c.source_id=d.source_id AND c.period=d.period))"""
            conflict_rows = [
                dict(r) for r in conn.execute(cte + " SELECT * FROM conflicts LIMIT 240", params)
            ]
            filters = []
            filter_params = []
            if spec.start_period:
                filters.append("period_end(period)>=?")
                filter_params.append(period_bounds(spec.start_period)[0])
            if spec.end_period:
                filters.append("period_start(period)<=?")
                filter_params.append(period_bounds(spec.end_period)[1])
            tail = (" WHERE " + " AND ".join(filters)) if filters else ""
            if spec.operation == "coverage":
                sql = (
                    cte
                    + f" SELECT geography,metric,review_status,count(*) observation_count,max(period) latest_period FROM scoped{tail} GROUP BY geography,metric,review_status ORDER BY geography,metric LIMIT ?"
                )
            elif spec.operation == "conflicts":
                sql = cte + " SELECT * FROM conflicts" + tail + " LIMIT ?"
            elif spec.operation == "rank":
                sql = (
                    cte
                    + f""", latest AS (SELECT *,ROW_NUMBER() OVER(PARTITION BY {key} ORDER BY period DESC) latest_rank FROM eligible{tail}),
                    comparable AS (SELECT *,RANK() OVER(PARTITION BY metric,definition,publisher,unit,source_id,period ORDER BY value DESC) comparable_rank,
                    count(*) OVER(PARTITION BY metric,definition,publisher,unit,source_id,period) peer_count FROM latest WHERE latest_rank=1 AND review_status='APPROVED')
                    SELECT * FROM comparable ORDER BY metric,definition,geography LIMIT ?"""
                )
            else:
                lag = (
                    "CASE frequency WHEN 'Q' THEN 4 WHEN 'M' THEN 12 WHEN 'H' THEN 2 ELSE 1 END"
                    if spec.comparison == "yoy"
                    else "1"
                )
                cte += f""", lagged AS (SELECT *,LAG(value,{lag}) OVER(PARTITION BY {key} ORDER BY period) previous_value,
                    LAG(review_status,{lag}) OVER(PARTITION BY {key} ORDER BY period) previous_review_status,
                    LAG(period,{lag}) OVER(PARTITION BY {key} ORDER BY period) previous_period,
                    LAG(period_index,{lag}) OVER(PARTITION BY {key} ORDER BY period) previous_index,
                    LAG(id,{lag}) OVER(PARTITION BY {key} ORDER BY period) previous_observation_id,
                    AVG(value) OVER(PARTITION BY {key} ORDER BY period ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) rolling_candidate,
                    MIN(period_index) OVER(PARTITION BY {key} ORDER BY period ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) rolling_start,
                    COUNT(*) OVER(PARTITION BY {key} ORDER BY period ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) rolling_count,
                    MIN(CASE WHEN review_status='APPROVED' THEN 1 ELSE 0 END) OVER(PARTITION BY {key} ORDER BY period ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) rolling_approved,
                    GROUP_CONCAT(id) OVER(PARTITION BY {key} ORDER BY period ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) rolling_observation_ids,
                    ROW_NUMBER() OVER(PARTITION BY {key} ORDER BY period DESC) latest_rank FROM eligible),
                    calculated AS (SELECT *,CASE WHEN review_status!='APPROVED' OR COALESCE(previous_review_status,'APPROVED')!='APPROVED' THEN 'PENDING_REVIEW'
                    WHEN previous_value IS NULL THEN 'NO_PREVIOUS_PERIOD' WHEN period_index IS NULL OR previous_index IS NULL THEN 'UNSUPPORTED_FREQUENCY'
                    WHEN period_index-previous_index!={lag} THEN 'MISSING_PERIOD' ELSE 'COMPARABLE' END comparison_status FROM lagged)
                    SELECT *,CASE WHEN comparison_status='COMPARABLE' THEN ROUND(value-previous_value,8) END absolute_change,
                    CASE WHEN comparison_status='COMPARABLE' AND previous_value!=0 THEN ROUND((value-previous_value)*100.0/previous_value,8) END relative_change_pct,
                    CASE WHEN rolling_count=4 AND period_index-rolling_start=3 AND rolling_approved=1 THEN rolling_candidate END rolling_mean,
                    CASE WHEN unit='percent' THEN 'percentage points' ELSE unit END change_unit FROM calculated"""
                if spec.operation == "latest":
                    sql = (
                        "WITH filtered AS ("
                        + cte
                        + tail
                        + f"""), selected AS (SELECT *,ROW_NUMBER() OVER(PARTITION BY {key} ORDER BY period DESC) scope_rank FROM filtered)
                        SELECT * FROM selected WHERE scope_rank=1 ORDER BY metric,geography,definition LIMIT ?"""
                    )
                else:
                    sql = cte + tail + " ORDER BY metric,geography,definition,period LIMIT ?"
            rows = [dict(r) for r in conn.execute(sql, params + filter_params + [spec.limit])]
        for row in rows:
            row.pop("raw_path", None)
            row.pop("raw_hash", None)
            if (
                row.get("metric") in ["prime_rent", "grade_a_rent"]
                and "/year" in str(row.get("unit"))
                and not re.search(r"per\s+annum|p\.a\.|per\s+year", row.get("evidence_text", ""), re.I)
            ):
                row["candidate_unit"] = row["unit"]
                row["unit"] = row["unit"].replace("/year", "") + " (time denominator unconfirmed)"
                row["normalization_warning"] = (
                    "Annual time denominator not stated in original quote. No annual rent comparison is released."
                )
            if row.get("peer_count") == 1:
                row["comparable_rank"] = None
                row["rank_status"] = "NOT_COMPARABLE"
        ids = list(dict.fromkeys(r["document_id"] for r in rows if r.get("document_id")))
        return dict(
            rows=rows,
            conflicts=conflict_rows,
            integrity_failures=bad,
            evidence_ids=ids,
            status="SUCCESS" if rows else "INSUFFICIENT_EVIDENCE",
            query=spec.model_dump(),
            limitations=[
                "No cross-publisher or incompatible definitions are combined. Disclosed rounded inputs do not establish unrounded precision.",
                "Pending observations are for inspection only; computations and rankings require approval.",
            ],
        )
