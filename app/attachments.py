"""Private uploads are context, never approved market observations."""
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import fitz
from PIL import Image

from app.database import now, uid

MAX_BYTES = 8 * 1024 * 1024
MAX_TEXT = 24000
TYPES = {'.txt': 'text/plain', '.md': 'text/markdown', '.csv': 'text/csv', '.json': 'application/json',
         '.pdf': 'application/pdf', '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
         '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}


class AttachmentStore:
    def __init__(self, root):
        self.root = Path(root) / 'private' / 'attachments'
        self.root.mkdir(parents=True, exist_ok=True)

    def folder(self, owner):
        return self.root / hashlib.sha256(owner.encode()).hexdigest()

    def add(self, owner, name, raw):
        name = re.sub(r'[\x00-\x1f]', '', name.replace('\\', '/').split('/')[-1])[:120]
        suffix = Path(name).suffix.lower()
        if suffix not in TYPES or not raw or len(raw) > MAX_BYTES:
            raise ValueError('Upload a PDF, DOCX, text, CSV, JSON, PNG or JPEG file, up to 8 MiB.')
        text, kind = '', 'document'
        try:
            if suffix == '.pdf':
                with fitz.open(stream=raw, filetype='pdf') as pdf:
                    if pdf.is_encrypted or len(pdf) > 30:
                        raise ValueError('PDFs must be unencrypted and at most 30 pages.')
                    for page in pdf:
                        text += page.get_text()[:MAX_TEXT + 1] + '\n'
                        if len(text) > MAX_TEXT:
                            break
            elif suffix == '.docx':
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    entries = archive.infolist()
                    if len(entries) > 500 or sum(x.file_size for x in entries) > 20 * 1024 * 1024:
                        raise ValueError('DOCX expanded content exceeds its safe extraction limit.')
                    doc = archive.getinfo('word/document.xml')
                    if doc.file_size > 2 * 1024 * 1024:
                        raise ValueError('DOCX text exceeds its extraction limit.')
                    xml = archive.read(doc)
                    if b'<!DOCTYPE' in xml or b'<!ENTITY' in xml:
                        raise ValueError('Embedded XML entities are not supported.')
                    tree = ElementTree.fromstring(xml)
                    text = '\n'.join(x.text or '' for x in tree.iter() if x.tag.endswith('}t'))
            elif suffix in {'.png', '.jpg', '.jpeg'}:
                with Image.open(io.BytesIO(raw)) as im:
                    if im.width * im.height > 12_000_000 or im.format != ('PNG' if suffix == '.png' else 'JPEG'):
                        raise ValueError('Images must match their file type and be at most 12 million pixels.')
                    im.verify()
                kind = 'image'
            else:
                text = raw.decode('utf-8-sig')
                if '\x00' in text or any(ord(c) < 9 for c in text):
                    raise ValueError('The file is binary, not UTF-8 text.')
        except ValueError:
            raise
        except Exception:
            raise ValueError('This file could not be read safely. Use an unencrypted PDF, DOCX, valid image or UTF-8 text.') from None
        if kind == 'document' and not text.strip():
            raise ValueError('No readable text was found. Scanned PDFs need OCR before upload.')
        folder = self.folder(owner)
        folder.mkdir(parents=True, exist_ok=True)
        if sum(p.stat().st_size for p in folder.iterdir() if p.is_file()) + len(raw) > 100 * 1024 * 1024:
            raise ValueError('Your private upload storage limit is 100 MiB.')
        ident = uid()
        item = {'id': ident, 'name': name, 'mime': TYPES[suffix], 'kind': kind, 'bytes': len(raw),
                'sha256': hashlib.sha256(raw).hexdigest(), 'created_at': now(), 'review_status': 'USER_UPLOAD_UNVERIFIED',
                'text': text[:MAX_TEXT], 'truncated': len(text) > MAX_TEXT}
        (folder / (ident + '.bin')).write_bytes(raw)
        (folder / (ident + '.json')).write_text(json.dumps(item), encoding='utf-8')
        return {k: v for k, v in item.items() if k != 'text'}

    def get(self, owner, ident):
        if not re.fullmatch(r'[a-f0-9]{32}', ident):
            raise ValueError('Attachment not found for this user.')
        path = self.folder(owner) / (ident + '.json')
        if not path.is_file():
            raise ValueError('Attachment not found for this user.')
        return json.loads(path.read_text(encoding='utf-8'))

    def raw_path(self, owner, ident):
        self.get(owner, ident)
        return self.folder(owner) / (ident + '.bin')

    def context(self, owner, identifiers):
        if len(identifiers) > 5 or len(set(identifiers)) != len(identifiers):
            raise ValueError('Attach at most five different files per message.')
        result = [self.get(owner, ident) for ident in identifiers]
        if sum(len(x['text']) for x in result) > MAX_TEXT:
            raise ValueError('Combined extracted attachment text is limited to 24,000 characters. Use fewer files.')
        for item in result:
            if item['kind'] == 'image':
                import base64
                item['data_url'] = 'data:' + item['mime'] + ';base64,' + base64.b64encode(self.raw_path(owner, item['id']).read_bytes()).decode()
        return result
