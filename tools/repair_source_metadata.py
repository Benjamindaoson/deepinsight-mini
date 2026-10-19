"""Repair prior publication metadata from retained primary HTML, preserving audit history."""
from pathlib import Path
from app.database import Store
from app.skills.source_reader import publication_date, parse_date, digest, normalize

s = Store()
count = 0
for row in s.query("SELECT d.* FROM documents d JOIN sources s ON s.id=d.source_id WHERE json_extract(s.config,'$.collection_method')='html'"):
    html = Path(row["raw_path"]).read_text(encoding="utf-8", errors="replace")
    corrected = parse_date(publication_date(html))
    if corrected and corrected != row["published_at"]:
        s.execute("UPDATE documents SET published_at=? WHERE id=?", (corrected,row["id"]))
        seen=set()
        for event in s.query("SELECT * FROM events WHERE document_id=? ORDER BY discovered_at", (row["id"],)):
            if event['event_type'] in seen:
                s.execute("UPDATE events SET status='REJECTED' WHERE id=?",(event['id'],))
                s.audit('DUPLICATE_EVENT_QUARANTINED',event['id'],{'reason':'Same document and event type; inconsistent metadata must not create another event.'})
                continue
            seen.add(event['event_type'])
            identity = digest(normalize(event["title"].lower()) + event["event_type"] + str(corrected))
            s.execute("UPDATE events SET published_at=?,entity_key=? WHERE id=?", (corrected,identity,event["id"]))
        s.audit("PUBLICATION_METADATA_CORRECTED", row["id"], {"old":row["published_at"],"new":corrected,"basis":"explicit primary article time element"})
        count += 1
print({"publication_dates_corrected_from_original_evidence":count})
