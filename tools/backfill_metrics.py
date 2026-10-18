"""Idempotent extraction from existing original evidence; all new observations remain pending."""
import json
from app.database import Store
from app.skills.market_data import extract_observations
from app.skills.source_reader import registry

s=Store()
sources={x['id']:x for x in registry()}
count=0
for doc in s.query("SELECT * FROM documents WHERE status='SOURCE_VERIFIED'"):
    source=sources.get(doc['source_id'])
    if not source:
        continue
    doc['pages']=json.loads(doc['pages'] or '[]')
    for o in extract_observations(doc,source):
        count+=s.execute('''INSERT OR IGNORE INTO observations
          (id,document_id,metric,geography,period,value,unit,definition,publisher,evidence_text,page,review_status)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',(o['id'],doc['id'],o['metric'],o['geography'],o['period'],o['value'],o['unit'],o['definition'],o['publisher'],o['evidence_text'],o['page'],o['review_status']))
        if source['id']=='boe_bank_rate':
            s.execute("UPDATE observations SET evidence_text=? WHERE document_id=? AND metric=? AND period=? AND value=? AND review_status='PENDING_REVIEW'",
                (o['evidence_text'],doc['id'],o['metric'],o['period'],o['value']))
s.audit('METRIC_EXTRACTION_BACKFILL','retained_original_documents',{'new_pending_observations':count})
print({'new_pending_observations':count})
