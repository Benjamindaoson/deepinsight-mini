"""Retain, but quarantine, historical RSS items outside the current explicit collection scope."""
import re

from app.database import Store

s = Store()
count = 0
for row in s.query("SELECT id,title,text FROM documents WHERE source_id='city_news_feed' AND status='SOURCE_VERIFIED'"):
    if not re.search(r"office (?:scheme|space|building|development|market)|planning (?:approv|application)|City Plan 2040|pre-let|office-led", row["title"], re.I):
        s.execute("UPDATE documents SET status='REJECTED' WHERE id=?", (row["id"],))
        s.audit("SCOPE_REJECTED", row["id"], {"reason": "Article is outside the London office market collection scope."})
        count += 1
s.invalidate()
print({"quarantined_out_of_scope_articles": count, "preserved_history": True})
