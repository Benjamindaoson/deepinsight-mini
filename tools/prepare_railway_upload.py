"""Curated public seed and exact deploy context; never copy private DB or vault."""
import hashlib
import json
import os
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

from app.config import ROOT, config
from app.database import Store
from app.providers import ProviderVault


def main():
    stage = ROOT/'output/railway-upload'
    if stage.exists():
        raise SystemExit('Preserve the previous upload context. Use a new path for a revised release.')
    seed = stage/'deployment/seed'
    (seed/'raw').mkdir(parents=True)
    (seed/'reports').mkdir()
    source = Store()
    dest = Store(seed/'market.sqlite3')
    tables = ['sources','documents','observations','events','document_states','document_revisions']
    with source.connection() as origin, dest.connection() as target:
        for table in tables:
            rows = origin.execute('SELECT * FROM '+table).fetchall()
            for row in rows:
                value = dict(row)
                if table == 'documents':
                    raw = Path(value['raw_path'])
                    if not raw.is_file() or hashlib.sha256(raw.read_bytes()).hexdigest()!=value['raw_hash']:
                        raise ValueError('A retained public original failed its hash check.')
                    name = value['raw_hash'] + raw.suffix
                    shutil.copy2(raw,seed/'raw'/name)
                    value['raw_path']='/persist/data/raw/'+name
                    target.execute('INSERT INTO document_search(id,title,text) VALUES (?,?,?)',(value['id'],value['title'],value['text']))
                columns=list(value)
                target.execute('INSERT OR REPLACE INTO '+table+' ('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')',list(value.values()))
        run = origin.execute("SELECT * FROM monitor_runs WHERE status='SUCCESS' AND finished_at IS NOT NULL ORDER BY finished_at DESC LIMIT 1").fetchone()
        if run:
            target.execute('INSERT INTO monitor_runs VALUES ('+','.join('?' for _ in run)+')',tuple(run))
            report = origin.execute('SELECT * FROM reports WHERE id=?',(run['report_id'],)).fetchone()
            if report:
                value=dict(report)
                for key,suffix in [('html_path','.html'),('email_path','-email.html')]:
                    raw=Path(value[key])
                    name=value['id']+suffix
                    shutil.copy2(raw,seed/'reports'/name)
                    value[key]='/persist/output/reports/'+name
                value['pdf_path']=None
                target.execute('INSERT INTO reports VALUES ('+','.join('?' for _ in value)+')',list(value.values()))
        for key,value in [('morning_time','08:00'),('evening_time','18:00'),('notification_mode','disabled'),('scheduled_ai_analysis',True)]:
            target.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',(key,json.dumps(value)))
    with closing(sqlite3.connect(dest.path)) as conn:
        conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    # The source directories are the actual Mini implementation, without caches.
    for directory in ['app','deepinsight','config']:
        shutil.copytree(ROOT/directory,stage/directory,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in ['Dockerfile','railway.toml','.dockerignore','.railwayignore']:
        shutil.copy2(ROOT/name,stage/name)
    lock=(ROOT/'requirements.lock').read_text(encoding='utf-8-sig').splitlines()
    excluded={'playwright','greenlet','pytest','ruff','iniconfig','pluggy','colorama'}
    runtime=[row for row in lock if row.strip() and row.split('==')[0].lower() not in excluded]
    if not any(row.lower().startswith('cryptography==') for row in runtime):
        import importlib.metadata
        for name in ['cryptography','cffi','pycparser']:
            runtime.append(name+'=='+importlib.metadata.version(name))
    (ROOT/'deployment/requirements-runtime.txt').write_text('\n'.join(runtime)+'\n')
    shutil.copy2(ROOT/'deployment/requirements-runtime.txt',stage/'deployment/requirements-runtime.txt')
    # Compare bytes against real keys, but emit counts only.
    needles=[item['key'].encode() for item in ProviderVault(config().data).read('workspace')['profiles']]
    needles.extend(os.environ[name].encode() for name in ['MINI_API_KEY','LLM_API_KEY'] if os.getenv(name))
    files=[p for p in stage.rglob('*') if p.is_file()]
    if any(secret in p.read_bytes() for p in files for secret in needles):
        raise SystemExit('Actual credential detected in deployment package; upload stopped.')
    manifest={'source':str(ROOT),'stage':str(stage),'public_seed_observations':dest.one('SELECT count(*) n FROM observations')['n'],
              'private_conversations':dest.one('SELECT count(*) n FROM conversations')['n'],'secret_matches':0,
              'files':[{'path':str(p.relative_to(stage)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
    receipt=ROOT/'output/evidence/railway'
    receipt.mkdir(parents=True,exist_ok=True)
    (receipt/'upload-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'stage':str(stage),'files':len(files),'bytes':sum(p.stat().st_size for p in files),'observations':manifest['public_seed_observations'],'private_conversations':0,'secret_matches':0}))


if __name__=='__main__':
    main()
