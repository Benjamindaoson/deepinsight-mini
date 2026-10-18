from app.database import Store
from app.dashboard import dashboard, TOPICS
from app.skills.market_data import extract_observations
from fastapi.testclient import TestClient
from app.main import create_app


def test_default_is_chat_and_navigation_order(tmp_path):
    c=TestClient(create_app(Store(tmp_path/'db.sqlite')),base_url='http://localhost')
    body=c.get('/').text
    assert 'chat-composer' in body
    assert body.index('>Ask AI</a>') < body.index('>Overview</a>')
    assert c.get('/overview').status_code==200


def test_assessment_topics_and_gaps_are_explicit(tmp_path):
    data=dashboard(Store(tmp_path/'db.sqlite'))
    assert {'rents','vacancy','leasing','pipeline','submarkets','macro','demand','events'} <= {t['id'] for t in TOPICS}
    assert 'Midtown / Fringe' in data['submarkets']
    assert not data['approved_charts']
    assert all(t['question'] and t['source_targets'] for t in data['topics'])


def test_pending_value_visible_without_becoming_an_approved_chart(tmp_path):
    s=Store(tmp_path/'db.sqlite')
    s.execute("INSERT INTO sources(id,status) VALUES ('s','HEALTHY')")
    s.execute("INSERT INTO documents(id,source_id,status) VALUES ('d','s','SOURCE_VERIFIED')")
    s.execute("INSERT INTO observations(id,document_id,metric,geography,period,value,unit,definition,publisher,review_status) VALUES ('o','d','vacancy_rate','City','2026Q2',7.0,'percent','overall','Fixture','PENDING_REVIEW')")
    data=dashboard(s)
    assert data['observations'][0]['value']==7.0
    assert data['observations'][0]['review_status']=='PENDING_REVIEW'
    assert data['approved_charts']==[]


def test_real_style_report_extracts_take_up_supply_and_demand():
    doc={'text':'take-up reaching 2.4 million sq ft across 192 transactions. Supply across Central London fell to 18.7 million sq ft during the quarter. The vacancy rate declined by 20 bps to 7.2%. Grade A office space, which accounted for 94% of H1 take-up.','publisher':'Fixture','pages':[]}
    rows=extract_observations(doc,{'id':'savills_q2_2026'})
    assert {'take_up','availability','vacancy_rate','grade_a_take_up_share'} <= {r['metric'] for r in rows}
    assert all(r['review_status']=='PENDING_REVIEW' for r in rows)


def test_official_raw_api_history_is_separate_from_approved_market_chart(tmp_path):
    s=Store(tmp_path/'db.sqlite')
    s.execute("INSERT INTO sources(id,status) VALUES ('ons_cpi','HEALTHY')")
    raw='{"months": [{"date": "2026 JUL", "value": "3.0"}, {"date": "2026 AUG", "value": "3.1"}]}'
    s.execute("INSERT INTO documents(id,source_id,text,status) VALUES ('d','ons_cpi',?,'SOURCE_VERIFIED')",(raw,))
    for ident,period,value,quote in [('a','2026M07',3.0,'{"date": "2026 JUL", "value": "3.0"}'),('b','2026M08',3.1,'{"date": "2026 AUG", "value": "3.1"}')]:
        s.execute("INSERT INTO observations(id,document_id,metric,geography,period,value,unit,definition,publisher,evidence_text,review_status) VALUES (?,'d','cpi_inflation','UK',?,?,'percent','CPI annual rate','ONS',?,'PENDING_REVIEW')",(ident,period,value,quote))
    result=dashboard(s)
    assert len(result['source_history'])==1
    assert not result['approved_charts']
    s.execute("UPDATE observations SET value=99 WHERE id='b'")
    assert not dashboard(s)['source_history']
