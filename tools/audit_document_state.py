import json
from pathlib import Path
from app.database import Store
from app.skills.source_reader import publication_date,registry,parse_date

s=Store()
source=registry()[0]
rows=s.query("SELECT * FROM documents WHERE source_id='savills_q2_2026'")
for r in rows:
    raw=Path(r['raw_path']).read_text(encoding='utf-8',errors='replace')
    print(json.dumps({k:r[k] for k in ('id','url','status','published_at','previous_id','version','hash')} |
        {'current_parser_date':publication_date(raw,source.get('publication_date')),'parsed':parse_date(publication_date(raw,source.get('publication_date')))},indent=2))
print(json.dumps(s.query("SELECT e.id,e.document_id,e.published_at,e.title,d.status FROM events e JOIN documents d ON d.id=e.document_id WHERE d.source_id='savills_q2_2026'"),indent=2))
