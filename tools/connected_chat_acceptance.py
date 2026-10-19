"""Real browser and real-provider acceptance; no mocked model results."""
import json

from playwright.sync_api import sync_playwright, expect

from app.browser import launch_chromium
from app.config import ROOT, config
from app.providers import ProviderVault

OUT = ROOT / 'output/evidence/connected-chat'
OUT.mkdir(parents=True, exist_ok=True)
checks, errors, jobs = [], [], []


def record(name, **details):
    checks.append({'name': name, 'status': 'PASS', **details})


def main():
    with sync_playwright() as p:
        browser = launch_chromium(p)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        def response_received(response):
            if '/api/jobs/' in response.url and response.status == 200:
                try:
                    data = response.json()
                    if data['status'] != 'RUNNING' and not any(x['id'] == data['id'] for x in jobs):
                        jobs.append(data)
                except Exception:
                    pass
        page.on('response', response_received)
        page.goto('http://127.0.0.1:8766/', wait_until='networkidle')
        page.get_by_role('button', name='New conversation', exact=True).click()
        expect(page.locator('#chat-model option')).not_to_have_count(1)
        font = page.locator('#question').evaluate('(e)=>getComputedStyle(e).fontSize')
        assert float(font[:-2]) >= 18
        page.screenshot(path=str(OUT / 'chat-desktop.png'))
        page.locator('#model-menu summary').click()
        expect(page.locator('#chat-model')).to_be_visible()
        page.locator('#chat-model').select_option(label='gpt-5.6-terra')
        page.locator('#chat-thinking').select_option('low')
        expect(page.locator('#model-selection-status')).to_have_text('Selection saved.')
        page.screenshot(path=str(OUT / 'model-menu.png'))
        page.keyboard.press('Escape')
        record('desktop_typography_and_model_thinking', font=font, model='gpt-5.6-terra', thinking='low')

        page.goto('http://127.0.0.1:8766/settings#api-connection', wait_until='networkidle')
        key = next(x['key'] for x in ProviderVault(config().data).read('workspace')['profiles'] if x['provider'] == 'toapis')
        page.locator('#provider-label').fill('Acceptance personal connection')
        page.locator('#provider-key').fill(key)
        page.get_by_role('button', name='Save encrypted key', exact=True).click()
        expect(page.locator('#provider-result')).to_contain_text('model catalog loaded', timeout=45000)
        assert page.locator('#provider-key').input_value() == ''
        state = page.request.get('http://127.0.0.1:8766/api/providers').json()
        assert key not in json.dumps(state)
        personal = next(x for x in state['profiles'] if x['scope'] == 'personal')
        page.locator('#settings-model').select_option(personal['id'] + '|gpt-5.6-terra')
        page.locator('#settings-thinking').select_option('low')
        expect(page.locator('#model-selection-status')).to_have_text('Selection saved.')
        card = page.locator('.provider-card').filter(has=page.get_by_role('heading', name='Acceptance personal connection', exact=True))
        card.get_by_role('button', name='Test connection', exact=True).click()
        expect(card.locator('.actions + p')).to_contain_text('SUCCESS', timeout=90000)
        page.screenshot(path=str(OUT / 'api-settings.png'), full_page=True)
        record('personal_key_save_catalog_and_real_check', no_secret_echo=True)

        page.goto('http://127.0.0.1:8766/', wait_until='networkidle')
        page.get_by_role('button', name='New conversation', exact=True).click()
        with page.expect_file_chooser() as chooser:
            page.get_by_role('button', name='Add files or photos', exact=True).click()
        chooser.value.set_files({'name': 'acceptance-note.txt', 'mimeType': 'text/plain', 'buffer': b'Attachment verification phrase: Copper heron visits the quiet river.'})
        expect(page.locator('#queued-attachments')).to_contain_text('acceptance-note.txt', timeout=15000)
        page.locator('#question').fill('Use search_document_evidence to investigate current London office planning evidence and query_market_metrics to inspect vacancy data with review_status ALL. Do not approve numbers. Return a short nonnumeric exact source quote if available. Also include the exact verification phrase from my uploaded note in attachment_quotes, using its attachment_id. The file is unverified user context, not a source of market facts.')
        page.get_by_role('button', name='Research question', exact=True).click()
        expect(page.locator('#chat-history .chat-entry:not(.user)')).to_be_visible(timeout=210000)
        ask = next(x for x in reversed(jobs) if x['kind'] == 'ask')
        result = ask['result']
        (OUT / 'live-agent.json').write_text(json.dumps(ask, indent=2), encoding='utf-8')
        assert result['status'] == 'SUCCESS', result.get('message')
        assert result['tool_calls'] > 0
        assert any('Copper heron' in x['quote'] for x in result.get('attachment_quotes', [])), 'Model did not return a valid file quote'
        page.screenshot(path=str(OUT / 'live-agent-attachment.png'), full_page=True)
        record('real_agent_tools_and_attachment_read', model=result['model'], actual_tools=result['tool_calls'], run_id=result['agent_run_id'])

        page.goto('http://127.0.0.1:8766/overview', wait_until='networkidle')
        page.locator('select[name="status"]').select_option('ALL')
        expect(page.locator('#bi-status')).to_contain_text('inspection mode', timeout=30000)
        assert page.locator('#bi-kpis .bi-kpi').count() > 8
        assert page.locator('.bi-chart svg').count() > 3
        page.screenshot(path=str(OUT / 'dashboard-desktop.png'))
        page.locator('select[name="geography"]').select_option('City')
        expect(page.locator('#bi-status')).to_contain_text('inspection mode')
        page.wait_for_timeout(500)
        assert all('City' in x for x in page.locator('#bi-kpis .bi-kpi small').all_text_contents() if ' · ' in x and ('percent' in x or 'sq ft' in x))
        page.locator('select[name="metric"]').select_option('vacancy_rate')
        page.wait_for_timeout(500)
        page.get_by_role('button', name='Inspect source ↗').first.click()
        expect(page.locator('#bi-evidence')).to_be_visible()
        assert page.locator('#bi-evidence blockquote').inner_text()
        page.screenshot(path=str(OUT / 'dashboard-evidence.png'))
        page.locator('#bi-close-evidence').click()
        page.locator('select[name="geography"]').select_option('Canary Wharf')
        page.wait_for_timeout(500)
        expect(page.locator('#bi-kpis')).to_contain_text('Not Verified')
        page.locator('select[name="status"]').select_option('APPROVED')
        page.wait_for_timeout(500)
        expect(page.locator('#bi-status')).to_contain_text('approved')
        record('dashboard_sql_filters_echarts_evidence_and_missing_data')

        mobile_context = browser.new_context(viewport={'width': 390, 'height': 844})
        mobile = mobile_context.new_page()
        for path in ['/', '/overview', '/monitor', '/reports', '/settings']:
            mobile.goto('http://127.0.0.1:8766' + path, wait_until='networkidle')
            assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth + 2'), path
        mobile.goto('http://127.0.0.1:8766/', wait_until='networkidle')
        mobile.screenshot(path=str(OUT / 'chat-mobile.png'))
        record('five_pages_mobile_no_overflow')
        assert not errors, errors
        browser.close()
    receipt = {'status': 'PASS', 'checks': checks, 'page_errors': errors, 'real_agent': 'SUCCESS', 'scope': 'Actual local production app; real supplied providers; no external recipient send.'}
    (OUT / 'browser-acceptance.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
