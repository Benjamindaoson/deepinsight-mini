from pydantic import Field
from app.tools.contracts import Input, document


class EventInput(Input):
    geography: str = Field(default="", max_length=100)
    event_type: str = Field(default="", max_length=100)
    limit: int = Field(default=30, ge=1, le=100)


def get_market_events(store, args):
    rows = store.query(
        """SELECT e.*,d.url,d.publisher,d.raw_hash FROM events e JOIN documents d ON d.id=e.document_id
        WHERE e.status='SOURCE_VERIFIED' AND d.status='SOURCE_VERIFIED' AND (?='' OR e.geography=?)
        AND (?='' OR e.event_type=?) ORDER BY e.published_at DESC,e.discovered_at DESC LIMIT ?""",
        (args.geography, args.geography, args.event_type, args.event_type, args.limit),
    )
    eligible = []
    for row in rows:
        try:
            doc = document(store, row["document_id"])
        except ValueError:
            continue
        if row.get("evidence_text") and row["evidence_text"] in doc["text"]:
            eligible.append(row)
    return dict(
        events=eligible,
        evidence_ids=list(dict.fromkeys(e["document_id"] for e in eligible)),
        warnings=[
            "Events retain publication and discovery dates separately. Potential effects are not observed outcomes."
        ],
    )


def deduplicate_events(store, args):
    result = get_market_events(store, args)
    result["events"] = list({row.get("entity_key") or row["id"]: row for row in result["events"]}.values())
    result["deduplication"] = "Existing canonical entity identities; source history is retained."
    return result
