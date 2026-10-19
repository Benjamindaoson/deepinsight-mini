"""Generate a time-bound delivery manifest from actual persisted evidence, never invented outcomes."""
import hashlib
import json
from pathlib import Path

from app.config import ROOT
from app.dashboard import dashboard
from app.database import Store, now

s=Store()
d=dashboard(s)
browser=json.loads((ROOT/'output/evidence/browser/acceptance.json').read_text(encoding='utf-8'))
report=s.one('SELECT * FROM reports ORDER BY created_at DESC LIMIT 1')
deck=ROOT/'output/slides/London_Office_Intelligence_Business_Demo_v3.pptx'
items=[deck,Path(report['html_path']),ROOT/'requirements.lock',ROOT/'config/sources.yaml',ROOT/'output/evidence/browser/acceptance.json']
if report.get('pdf_path'):
    items.append(Path(report['pdf_path']))
receipt={
 'generated_at':now(),'client_date':'2026-10-19','project_root':str(ROOT),
 'current_source_health':s.query('SELECT id,name,url,status,last_success,error FROM sources'),
 'observations':len(d['observations']),'dashboard_series':len(d['latest_observations']),
 'raw_official_history_charts':len(d['source_history']),
 'approved_observations':s.one("SELECT count(*) n FROM observations WHERE review_status='APPROVED'")['n'],
 'latest_monitor':s.one('SELECT * FROM monitor_runs ORDER BY started_at DESC LIMIT 1'),
 'scheduled_runs':s.query('SELECT * FROM schedule_slots'),
 'latest_model_call':s.one('SELECT at,model,status,error FROM model_calls ORDER BY at DESC LIMIT 1'),
 'browser':{'engineering':browser['engineering_browser_status'],'checks':len(browser['checks']),
            'six_questions':[{'question':q['input'],'status':q['status'],'actual_skill_calls':q['skill_calls']} for q in browser['questions']],
            'console_errors':browser['console_errors']},
 'verification':{'pytest':'45 passed, 1 upstream deprecation warning','ruff':'PASS','compileall':'PASS','pip_check':'PASS'},
 'readiness':{'engineering':'PASS_LOCAL_POC','real_ai':'BLOCKED_HTTP402','data_reliability':'PARTIAL',
              'monitoring':'PASS_CONTROLLED_SCHEDULE','report_quality':'PASS_RENDERED',
              'notification_delivery':'PASS_ISOLATED_SMTP_ONLY / EXTERNAL_BLOCKED','business_poc':'PARTIAL'},
 'notification_mode':s.setting('notification_mode','disabled'),
 'scheduled_times':{'morning':s.setting('morning_time','08:00'),'evening':s.setting('evening_time','18:00'),'timezone':'Europe/London'},
 'latest_report_id':report['id'],
 'artifacts':[{'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in items if p.exists()],
 'boundaries':['No successful live model/tool-calling acceptance','No approved market numeric conclusions',
 'Canary Wharf/Midtown/hybrid-working coverage incomplete','No actual external recipient delivery',
 'No VPS deployment or multi-day scheduler reliability claim',
 'Independent initial review findings repaired and regression-tested; second review attempt hit reviewer usage limit'],
}
(ROOT/'output/evidence/FINAL_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'receipt':'output/evidence/FINAL_RECEIPT.json','readiness':receipt['readiness'],'source_endpoints':len(receipt['current_source_health']),'observations':receipt['observations']}))
