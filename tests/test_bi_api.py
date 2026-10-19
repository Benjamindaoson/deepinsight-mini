import re

from fastapi.testclient import TestClient

from app.database import Store
from app.main import create_app


def test_bi_filters_reach_parameterized_sql_and_reject_arbitrary_sql(tmp_path):
    client = TestClient(create_app(Store(tmp_path / 'db.sqlite')), base_url='http://localhost')
    result = client.get('/api/analytics?metric=prime_rent&geography=City&start_period=2026Q1&end_period=2026Q2&review_status=ALL')
    assert result.status_code == 200
    query = result.json()['query']
    assert query['metric'] == 'prime_rent'
    assert query['geographies'] == ['City']
    assert query['start_period'] == '2026Q1'
    assert client.get('/api/analytics?metric=DROP%20TABLE').status_code == 400
    assert client.get('/api/analytics?sql=SELECT%20*%20FROM%20settings').status_code == 400


def test_model_input_cannot_request_foreign_conversation(tmp_path):
    store = Store(tmp_path / 'db.sqlite')
    store.execute("INSERT INTO conversations VALUES ('foreign','now','now','[]')")
    store.execute("INSERT INTO conversation_owners VALUES ('foreign','another-owner')")
    client = TestClient(create_app(store), base_url='http://localhost')
    token = re.search(r'name="csrf-token" content="([^"]+)"', client.get('/').text).group(1)
    assert client.get('/api/conversations/foreign').status_code == 404
    assert client.get('/api/agent/conversations/foreign').status_code == 404
    assert client.post('/api/ask', json={'question': 'Open it', 'conversation_id': 'foreign'}, headers={'X-CSRF-Token': token}).status_code == 400
