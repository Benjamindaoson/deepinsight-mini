"""Approved model transports and owner-bound, DPAPI-encrypted secrets.

Public metadata is deliberately key-free. Windows vaults are decryptable only
by the OS account running this app. Linux deployments use environment keys;
personal persistence fails closed until an OS secret-store adapter is provided.
"""
import base64
import hashlib
import json
import os
import re
import threading
import time
from dataclasses import replace
from pathlib import Path

import httpx

from app.config import config
from app.database import now, uid
from app.secrets import protect

PROVIDERS = {
    'toapis': {'label': 'ToAPIs', 'base_url': 'https://toapis.cn/v1'},
    'deepseek': {'label': 'Official DeepSeek', 'base_url': 'https://api.deepseek.com'},
}
_lock = threading.RLock()


def seal(raw, decrypt=False):
    return protect(raw, decrypt=decrypt)


def capabilities(model):
    low = model.lower()
    if low.startswith('deepseek'):
        return {'thinking': ['auto', 'off', 'high', 'max'] if 'v4' in low or low in {'deepseek-flash', 'deepseek-pro'} else ['auto', 'off', 'high'], 'vision': False}
    if low.startswith('gpt-5') and not any(x in low for x in ('codex', 'pro-official')):
        return {'thinking': ['auto', 'low', 'medium', 'high'], 'vision': True}
    if low.startswith('gemini'):
        return {'thinking': ['auto'], 'vision': True}
    if low.startswith('claude'):
        return {'thinking': ['auto'], 'vision': True}
    return {'thinking': ['auto'], 'vision': low.startswith('gpt-4o')}


def request_parameters(c, max_tokens):
    if c.base_url not in {v['base_url'] for v in PROVIDERS.values()}:
        raise ValueError('Choose an approved HTTPS provider in Settings.')
    caps = capabilities(c.model)
    if c.thinking not in caps['thinking']:
        raise ValueError('This model does not support the selected thinking mode. Choose Auto or a supported option.')
    result = {'model': c.model, 'max_tokens': max_tokens, 'stream': False}
    if c.model.lower().startswith('gpt-5'):
        result['max_completion_tokens'] = result.pop('max_tokens')
        if c.thinking != 'auto':
            result['reasoning_effort'] = c.thinking
    elif c.model.lower().startswith('deepseek'):
        if c.thinking != 'auto':
            result['extra_body'] = {'thinking': {'type': 'disabled' if c.thinking == 'off' else 'enabled'}}
            if c.thinking != 'off':
                result['reasoning_effort'] = c.thinking
    return result


class ProviderVault:
    def __init__(self, root):
        self.root = Path(root) / 'private' / 'providers'
        self.root.mkdir(parents=True, exist_ok=True)
        if os.name != 'nt':
            self.root.chmod(0o700)

    def path(self, owner):
        return self.root / (hashlib.sha256(owner.encode()).hexdigest() + '.sealed')

    def read(self, owner):
        path = self.path(owner)
        return json.loads(seal(base64.b64decode(path.read_bytes()), decrypt=True)) if path.exists() else {'profiles': [], 'selection': {}}

    def write(self, owner, data):
        path = self.path(owner)
        temporary = path.with_suffix('.' + uid() + '.tmp')
        temporary.write_bytes(base64.b64encode(seal(json.dumps(data).encode())))
        if os.name != 'nt':
            temporary.chmod(0o600)
        os.replace(temporary, path)

    def save(self, owner, data):
        allowed = {'id', 'provider', 'api_key', 'label'}
        if not isinstance(data, dict) or set(data) - allowed or data.get('provider') not in PROVIDERS:
            raise ValueError('Choose ToAPIs or Official DeepSeek. Custom endpoint overrides are not allowed.')
        key = data.get('api_key', '')
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_\-]{8,256}', key):
            raise ValueError('Enter a valid API key without spaces. Saved keys are never returned.')
        label = data.get('label') or PROVIDERS[data['provider']]['label']
        if not isinstance(label, str) or len(label) > 60 or re.search(r'[\x00-\x1f]', label):
            raise ValueError('Use a profile name up to 60 characters.')
        with _lock:
            state = self.read(owner)
            ident = data.get('id') or uid()
            if data.get('id') and not any(x['id'] == ident for x in state['profiles']):
                raise ValueError('Profile not found for this user.')
            if len(state['profiles']) >= 8 and not data.get('id'):
                raise ValueError('At most eight personal provider profiles are allowed.')
            item = {'id': ident, 'provider': data['provider'], 'label': label, 'key': key, 'models': [], 'updated_at': now(), 'check': None}
            state['profiles'] = [x for x in state['profiles'] if x['id'] != ident] + [item]
            self.write(owner, state)
        return self.safe(item)

    @staticmethod
    def safe(item):
        return {k: v for k, v in item.items() if k != 'key'} | {'credential_configured': bool(item.get('key')), 'base_url': PROVIDERS[item['provider']]['base_url']}

    def public(self, owner):
        own = self.read(owner)
        workspace = self.read('workspace') if owner != 'workspace' else {'profiles': []}
        return {'profiles': [self.safe(x) | {'scope': 'personal'} for x in own['profiles']] +
                [self.safe(x) | {'scope': 'workspace'} for x in workspace['profiles']], 'selection': own.get('selection', {})}

    def resolve(self, owner, ident):
        states = [self.read(owner)]
        if owner != 'workspace':
            states.append(self.read('workspace'))
        for state in states:
            for item in state['profiles']:
                if item['id'] == ident:
                    return dict(item) | {'base_url': PROVIDERS[item['provider']]['base_url']}
        raise ValueError('Provider profile not found for this user.')

    def update(self, owner, ident, **fields):
        with _lock:
            state = self.read(owner)
            for item in state['profiles']:
                if item['id'] == ident:
                    item.update(fields)
                    self.write(owner, state)
                    return
        raise ValueError('Only your personal profiles can be changed here.')

    def delete(self, owner, ident):
        with _lock:
            state = self.read(owner)
            if not any(x['id'] == ident for x in state['profiles']):
                raise ValueError('Only your personal profiles can be removed.')
            state['profiles'] = [x for x in state['profiles'] if x['id'] != ident]
            if state.get('selection', {}).get('profile_id') == ident:
                state['selection'] = {}
            self.write(owner, state)

    def select(self, owner, profile_id, model, thinking='auto'):
        item = self.resolve(owner, profile_id)
        if model not in [x['id'] for x in item['models']]:
            raise ValueError('Refresh models first and choose a model returned by this provider.')
        selected = replace(config(), key=item['key'], base_url=item['base_url'], model=model, thinking=thinking, provider=item['provider'])
        request_parameters(selected, 100)
        with _lock:
            state = self.read(owner)
            state['selection'] = {'profile_id': profile_id, 'model': model, 'thinking': thinking}
            self.write(owner, state)
        return selected

    def runtime(self, owner, selection=None):
        selected = selection or self.read(owner).get('selection') or {}
        if not selected:
            items = self.public(owner)['profiles']
            if not items:
                return config()
            item = items[0]
            if not item['models']:
                raise ValueError('Open API settings, refresh models and choose a model.')
            selected = {'profile_id': item['id'], 'model': item['models'][0]['id'], 'thinking': 'auto'}
        return self.select(owner, **selected)

    def catalog(self, owner, ident):
        item = self.resolve(owner, ident)
        if item.get('catalog_at') and time.time() - item['catalog_at'] < 5:
            raise ValueError('Wait a few seconds before refreshing the provider catalog.')
        try:
            with httpx.Client(timeout=25, follow_redirects=False) as client:
                with client.stream('GET', item['base_url'].rstrip('/') + '/models', headers={'Authorization': 'Bearer ' + item['key']}) as response:
                    if response.status_code != 200:
                        raise ValueError('Model catalog returned HTTP ' + str(response.status_code))
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > 2_000_000:
                            raise ValueError('Model catalog exceeded its response limit.')
                    rows = json.loads(body).get('data', [])
            models = []
            for row in rows[:1000]:
                name = row.get('id', '')
                if re.fullmatch(r'[A-Za-z0-9_.:/\-]{1,120}', name) and name.lower().startswith(('gpt-', 'claude-', 'gemini-', 'deepseek')) and not any(x in name.lower() for x in ('image', 'audio', 'tts', 'codex', 'nano-banana', 'realtime')) and not (name.startswith('gpt-') and 'pro-official' in name):
                    models.append({'id': name, **capabilities(name)})
            if not models:
                raise ValueError('The provider returned no supported chat models.')
            # Workspace presets are maintained by the operator, but authenticated
            # users may refresh their non-secret catalog, never read/write the key.
            target = owner if any(x['id'] == ident for x in self.read(owner)['profiles']) else 'workspace'
            self.update(target, ident, models=models, catalog_at=time.time(), catalog_checked_at=now())
            return {'status': 'SUCCESS', 'models': models, 'checked_at': now()}
        except httpx.HTTPError:
            raise ValueError('Provider catalog connection failed. Check connectivity and retry explicitly.') from None
