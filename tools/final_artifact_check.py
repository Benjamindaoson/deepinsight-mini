import hashlib
import json
import pymupdf as fitz
from app.config import ROOT
from app.database import Store

s=Store()
report=s.one('SELECT * FROM reports ORDER BY created_at DESC LIMIT 1')
pdf=fitz.open(report['pdf_path'])
text='\n'.join(p.get_text() for p in pdf)
assert '2026-08-06' in text
assert '2026-10-01' not in text
count=s.one("SELECT count(*) n FROM events e JOIN documents d ON d.id=e.document_id WHERE d.source_id='savills_q2_2026' AND e.status='SOURCE_VERIFIED'")['n']
assert count==1
folder=ROOT/'output/evidence/pdf-final'
folder.mkdir(parents=True,exist_ok=True)
for i,page in enumerate(pdf):
    assert len(page.get_text())>50
    page.get_pixmap(matrix=fitz.Matrix(1,1)).save(folder/f'page-{i+1}.png')
deck=ROOT/'output/slides/London_Office_Intelligence_Business_Demo_v3.pptx'
receipt=json.loads((ROOT/'output/slide-build/London_Office_Intelligence_Business_Demo_v3.pptx.validation.json').read_text(encoding='utf-8'))
hash_value=hashlib.sha256(deck.read_bytes()).hexdigest()
assert receipt['finalSha256']==hash_value
assert receipt['packageIntegrity']['status']=='pass'
assert receipt['firstPartyImport']['passed']
print(json.dumps({'status':'PASS','pdf_pages':len(pdf),'article_publication_date':'2026-08-06',
    'active_savills_events':count,'pptx_sha256':hash_value,'pptx_bytes':deck.stat().st_size}))
