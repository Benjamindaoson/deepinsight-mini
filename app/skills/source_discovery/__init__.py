from pydantic import Field
from app.tools.contracts import Input


class SearchInput(Input):
    query: str = Field(default="", max_length=500)


class FetchInput(Input):
    source_id: str = Field(min_length=1, max_length=120)


def search_market_sources(store, args):
    rows = store.query(
        "SELECT id,name,url,kind,status,last_success,error FROM sources WHERE name LIKE ? OR id LIKE ? ORDER BY id LIMIT 50",
        ("%" + args.query + "%", "%" + args.query + "%"),
    )
    return dict(
        sources=rows,
        evidence_ids=[],
        warnings=["Registered source coverage only; search does not prove new collection."],
    )


def search_document_evidence(store, args):
    from app.skills.research import research

    data = research(store, args.query)
    return data | {"evidence_ids": [x["id"] for x in data["evidence"]]}


def fetch_source_updates(store, args):
    from app.skills.source_reader import read_source, registry
    from app.skills.monitor import save_document

    source = next((s for s in registry() if s["id"] == args.source_id and s.get("enabled")), None)
    if not source:
        raise ValueError("SOURCE_NOT_ENABLED")
    documents = []
    for doc in read_source(source):
        saved = save_document(store, doc, source)
        if saved:
            documents.append(saved if isinstance(saved, str) else saved["id"])
    return dict(
        document_ids=documents,
        evidence_ids=documents,
        warnings=["Collection creates pending candidates, never approval."],
    )
