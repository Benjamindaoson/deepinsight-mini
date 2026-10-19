import json
import re
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.config import config
from app.database import Store
from app.main import create_app


def test_provider_profiles_encrypt_keys_and_isolate_owners(tmp_path):
    from app.providers import ProviderVault
    vault = ProviderVault(tmp_path)
    key = 'sk-test-private-never-return-this'
    saved = vault.save('alice', {'provider': 'toapis', 'api_key': key, 'label': 'My key'})
    assert key not in json.dumps(saved)
    assert key not in ''.join(p.read_text(errors='ignore') for p in tmp_path.rglob('*') if p.is_file())
    assert vault.resolve('alice', saved['id'])['key'] == key
    assert not vault.public('bob')['profiles']
    with pytest.raises(ValueError):
        vault.resolve('bob', saved['id'])


def test_provider_rejects_endpoint_injection_and_blank_key(tmp_path):
    from app.providers import ProviderVault
    vault = ProviderVault(tmp_path)
    for data in [{'provider': 'http://127.0.0.1', 'api_key': 'x'},
                 {'provider': 'toapis', 'base_url': 'https://evil.example', 'api_key': 'x'},
                 {'provider': 'toapis', 'api_key': ''}]:
        with pytest.raises(ValueError):
            vault.save('a', data)


def test_parameters_map_selected_thinking_and_never_change_model():
    from app.providers import request_parameters
    c = replace(config(), base_url='https://toapis.cn/v1', model='gpt-5.6-terra', thinking='high')
    params = request_parameters(c, 2000)
    assert params['model'] == 'gpt-5.6-terra'
    assert params['reasoning_effort'] == 'high'
    assert 'temperature' not in params
    d = replace(c, base_url='https://api.deepseek.com', model='deepseek-v4-flash', thinking='off')
    assert request_parameters(d, 2000)['extra_body']['thinking']['type'] == 'disabled'
    with pytest.raises(ValueError, match='thinking'):
        request_parameters(replace(c, model='unknown-model'), 100)


def test_attachment_contents_are_retained_with_ownership_and_bounds(tmp_path):
    from app.attachments import AttachmentStore
    files = AttachmentStore(tmp_path)
    item = files.add('alice', '../../briefing.txt', b'User document: demand is uncertain.')
    assert item['name'] == 'briefing.txt'
    content = files.context('alice', [item['id']])
    assert content[0]['text'] == 'User document: demand is uncertain.'
    assert content[0]['review_status'] == 'USER_UPLOAD_UNVERIFIED'
    with pytest.raises(ValueError):
        files.context('bob', [item['id']])
    with pytest.raises(ValueError):
        files.add('alice', 'script.exe', b'MZ\x00binary')
    with pytest.raises(ValueError):
        files.add('alice', 'bad.txt', b'\x00\xff')
    with pytest.raises(ValueError):
        files.add('alice', 'large.txt', b'x' * (8 * 1024 * 1024 + 1))


def test_personal_configuration_api_keeps_csrf_and_no_secret_echo(tmp_path):
    c = TestClient(create_app(Store(tmp_path / 'db.sqlite')), base_url='http://localhost')
    token = re.search(r'name="csrf-token" content="([^"]+)"', c.get('/').text).group(1)
    body = {'provider': 'toapis', 'label': 'Personal', 'api_key': 'sk-test-secret-key'}
    assert c.post('/api/providers', json=body).status_code == 403
    response = c.post('/api/providers', json=body, headers={'X-CSRF-Token': token})
    assert response.status_code == 200
    assert 'sk-test-secret-key' not in response.text
    assert 'sk-test-secret-key' not in c.get('/api/providers').text
    other = TestClient(c.app, base_url='http://localhost')
    assert not other.get('/api/providers').json()['profiles']


def test_owned_upload_endpoint_and_untrusted_request_content(tmp_path):
    c = TestClient(create_app(Store(tmp_path / 'db.sqlite')), base_url='http://localhost')
    token = re.search(r'name="csrf-token" content="([^"]+)"', c.get('/').text).group(1)
    res = c.post('/api/attachments', files={'file': ('note.txt', b'A genuine uploaded note.', 'text/plain')},
                 headers={'X-CSRF-Token': token})
    assert res.status_code == 200
    assert res.json()['review_status'] == 'USER_UPLOAD_UNVERIFIED'
    assert c.get('/api/attachments/' + res.json()['id']).status_code == 200
    other = TestClient(c.app, base_url='http://localhost')
    assert other.get('/api/attachments/' + res.json()['id']).status_code == 404


def test_uploaded_quotes_cannot_become_approved_source_claims():
    from app.agent import attachment_quotes
    uploaded = [{'id': 'owned', 'name': 'note.txt', 'kind': 'document', 'text': 'A source needs verification.'}]
    draft = {'attachment_quotes': [{'attachment_id': 'owned', 'quote': 'A source needs verification.'},
                                   {'attachment_id': 'owned', 'quote': 'Rent grew 99%.'},
                                   {'attachment_id': 'foreign', 'quote': 'A source needs verification.'}]}
    accepted = attachment_quotes(draft, uploaded)
    assert len(accepted) == 1
    assert accepted[0]['review_status'] == 'USER_UPLOAD_UNVERIFIED'
    assert accepted[0]['quote'] == uploaded[0]['text']


def test_runtime_selection_is_scoped_without_mutating_environment():
    from app.config import runtime_scope
    baseline = config()
    selected = replace(baseline, model='selected-test-model', key='private-test-only')
    with runtime_scope(selected):
        assert config().model == 'selected-test-model'
    assert config().model == baseline.model
