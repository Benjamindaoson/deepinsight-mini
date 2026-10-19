"""Freeze the actual P0 run, without credentials or invented market results."""
import hashlib
import json
from pathlib import Path

from app.config import ROOT
from app.database import Store, now
from app.tools.registry import registry


def main():
    store = Store()
    folder = ROOT / 'output/evidence/connected-chat'
    run = store.one("SELECT * FROM monitor_runs WHERE finished_at IS NOT NULL ORDER BY finished_at DESC LIMIT 1")
    report = store.one('SELECT id,data,html_path,email_path FROM reports WHERE id=?', (run['report_id'],))
    data = json.loads(report['data'])
    browser = json.loads((folder/'browser-acceptance.json').read_text(encoding='utf-8'))
    smtp = json.loads((ROOT/'output/evidence/smtp/receipt.json').read_text(encoding='utf-8'))
    tools = registry()
    paths = [ROOT/'output/p0-final-tests.txt',folder/'provider-probes.json',folder/'browser-acceptance.json',
             Path(report['html_path']),Path(report['email_path']),ROOT/'output/evidence/smtp/receipt.json']
    result = {'at':now(),'scope':'Actual local website and independent scheduled run; PDF development paused',
              'product_url':'http://127.0.0.1:8766/','dashboard_url':'http://127.0.0.1:8766/overview',
              'provider_tests':json.loads((folder/'provider-probes.json').read_text(encoding='utf-8')),
              'browser':browser,'skills':sorted({t.skill for t in tools.values()}),'registered_tools':len(tools),
              'monitor':run,'report':{'id':report['id'],'ai_status':data['ai_status'],'html_path':report['html_path'],
                                    'email_path':report['email_path'],'accepted_ai_claims':len((data.get('agent_analysis') or {}).get('claims',[]))},
              'observations':store.one('SELECT count(*) n FROM observations')['n'],
              'approved_observations':store.one("SELECT count(*) n FROM observations WHERE review_status='APPROVED'")['n'],
              'sources':store.query('SELECT id,status,last_success FROM sources'),
              'schedule':{'morning':store.setting('morning_time','08:00'),'evening':store.setting('evening_time','18:00'),'timezone':'Europe/London','independent':'Windows Task Scheduler; optional APScheduler worker uses shared durable slots'},
              'smtp':smtp,'notification_mode':store.setting('notification_mode','disabled'),
              'artifacts':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in paths],
              'boundaries':['Pending source figures remain unapproved; single periods do not establish trends.',
                            'Canary Wharf/Midtown and direct hybrid-working series still require additional lawful data.',
                            'No external recipient send, VPS deployment or long-term uptime claim.',
                            'Personal key persistence verified on Windows DPAPI; Linux needs native secret-store integration or environment keys.']}
    assert run['status']=='SUCCESS' and browser['status']=='PASS' and len(result['skills'])==8
    assert smtp['messages_received']==1 and result['schedule']['evening']=='18:00'
    (folder/'P0_DELIVERY_RECEIPT.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'status':'PASS','skills':8,'tools':len(tools),'scheduled_run':run['id'],'report_id':report['id'],'ai_status':data['ai_status'],'html_path':report['html_path'],'smtp_received':1},indent=2))


if __name__=='__main__':
    main()
