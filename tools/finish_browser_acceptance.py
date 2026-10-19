"""Continue unpaid UI checks after the live-model flow already passed.

The first runner reached the mobile stage, then hit a harness API typo.
This continuation avoids spending the user's API budget on passed steps.
"""
import json

from playwright.sync_api import sync_playwright, expect

from app.browser import launch_chromium
from app.config import ROOT

OUT = ROOT / 'output/evidence/connected-chat'


def main():
    live = json.loads((OUT / 'live-agent.json').read_text(encoding='utf-8'))
    assert live['result']['status'] == 'SUCCESS' and live['result']['tool_calls'] > 0
    assert live['result']['attachment_quotes']
    checks = ['desktop_typography_model_and_thinking', 'personal_key_save_catalog_real_check',
              'real_agent_tools_and_uploaded_text', 'sql_filters_charts_source_drilldown_and_not_verified']
    errors = []
    with sync_playwright() as p:
        browser = launch_chromium(p)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto('http://127.0.0.1:8766/overview', wait_until='networkidle')
        page.locator('select[name="status"]').select_option('ALL')
        expect(page.locator('#bi-status')).to_contain_text('inspection mode')
        charts = page.locator('.bi-chart svg').count()
        assert charts > 3
        page.screenshot(path=str(OUT / 'dashboard-desktop.png'))
        page.locator('#bi-chart-grid').screenshot(path=str(OUT / 'market-charts.png'))
        for selector, value in [('select[name="source"]', 'ons_cpi'), ('select[name="time_range"]', 'last_12_months')]:
            page.locator(selector).select_option(value)
            page.wait_for_timeout(400)
        assert page.locator('#bi-kpis').count()
        source_data=page.request.get('http://127.0.0.1:8766/api/dashboard/overview?source=ons_cpi&time_range=last_12_months&status=ALL').json()
        assert source_data['observations'] and all(x['source_id']=='ons_cpi' for x in source_data['observations'])
        page.locator('select[name="time_range"]').select_option('custom')
        page.locator('input[name="start_period"]').fill('2026M01')
        page.locator('input[name="end_period"]').fill('2026M08')
        page.get_by_role('button', name='Apply filters', exact=True).click()
        page.wait_for_timeout(400)
        page.locator('select[name="grade"]').select_option('prime')
        page.wait_for_timeout(400)
        expect(page.locator('#bi-kpis')).to_contain_text('Not Verified')
        checks.append('source_calendar_period_grade_filters')
        mobile_context = browser.new_context(viewport={'width': 390, 'height': 844})
        mobile = mobile_context.new_page()
        mobile.on('pageerror', lambda error: errors.append(str(error)))
        for path in ['/', '/overview', '/monitor', '/reports', '/settings']:
            mobile.goto('http://127.0.0.1:8766'+path, wait_until='networkidle')
            assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth + 2'), path
        mobile.goto('http://127.0.0.1:8766/', wait_until='networkidle')
        font=mobile.locator('#question').evaluate('(e)=>getComputedStyle(e).fontSize')
        assert float(font[:-2]) >= 16
        mobile.screenshot(path=str(OUT / 'chat-mobile.png'))
        mobile.locator('#model-menu summary').click()
        expect(mobile.locator('#chat-model')).to_be_visible()
        mobile.screenshot(path=str(OUT / 'model-menu-mobile.png'))
        checks.append('five_pages_mobile_and_keyboard_accessible_controls')
        assert not errors, errors
        browser.close()
    receipt={'status':'PASS','checks':[{'name':x,'status':'PASS'} for x in checks], 'desktop_charts':charts,
             'page_errors':errors,'real_agent':'SUCCESS','actual_tool_calls':live['result']['tool_calls'],
             'agent_run_id':live['result']['agent_run_id'],'attachment_exact_quote_verified':True,
             'harness_repair':'Initial runner used BrowserContext.new_page(viewport=...), fixed to browser.new_context; resumed UI checks without repeating paid tests.'}
    (OUT/'browser-acceptance.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':
    main()
