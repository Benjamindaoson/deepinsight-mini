import json
from app.tools.contracts import document


def extract_market_metrics(store, args):
    from app.skills.market_data import extract_observations

    doc = document(store, args.document_id)
    source = store.one("SELECT config FROM sources WHERE id=?", (doc["source_id"],))
    original = dict(doc, pages=json.loads(doc["pages"] or "[]"))
    rows = extract_observations(original, json.loads(source["config"] or "{}"))
    columns = [
        "id",
        "metric",
        "geography",
        "period",
        "value",
        "unit",
        "definition",
        "publisher",
        "evidence_text",
        "page",
        "review_status",
    ]
    for row in rows:
        assert row["review_status"] == "PENDING_REVIEW"
        store.execute(
            "INSERT OR IGNORE INTO observations(document_id,"
            + ",".join(columns)
            + ") VALUES ("
            + ",".join("?" for _ in range(len(columns) + 1))
            + ")",
            [doc["id"]] + [row.get(k) for k in columns],
        )
    return dict(
        candidates=len(rows),
        review_status="PENDING_REVIEW",
        evidence_ids=[doc["id"]],
        warnings=[
            "Extraction interpretations, including annual rent units, still require individual review."
        ],
    )


def validate_market_observations(store, args):
    from app.analytics.engine import Analytics, QuerySpec

    return Analytics(store).query(QuerySpec.model_validate(args.model_dump()))
