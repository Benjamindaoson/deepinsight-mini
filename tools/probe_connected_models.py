"""Explicit live checks. Credentials are loaded from the OS-encrypted vault."""
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

from app.agent import completion, provider_fingerprint
from app.config import config, runtime_scope
from app.database import Store, now
from app.providers import ProviderVault


def main():
    store, vault = Store(), ProviderVault(config().data)
    profiles = vault.read('workspace')['profiles']
    cases = [('toapis', 'gpt-5.6-terra', 'low'), ('toapis', 'gemini-2.5-flash-official', 'auto'),
             ('toapis', 'claude-haiku-4-5', 'auto'), ('deepseek', 'deepseek-flash', 'off')]
    def check(case):
        provider, model, thinking = case
        item = next(x for x in profiles if x['provider'] == provider)
        selected = replace(config(), key=item['key'], base_url=vault.resolve('workspace', item['id'])['base_url'],
                           model=model, thinking=thinking, provider=provider)
        with runtime_scope(selected):
            store.set_setting('model_block_' + provider_fingerprint(), None)
            try:
                response = completion(store, [{'role': 'user', 'content': 'Reply with exactly OK.'}], max_tokens=1200, timeout=50)
                text = response.choices[0].message.content or ''
                receipt = {'provider': provider, 'model': model, 'thinking': thinking, 'status': 'SUCCESS' if text.strip() else 'PARTIAL',
                           'response_model': response.model, 'visible_response': text[:80], 'at': now(),
                           'tokens': response.usage.model_dump() if response.usage else None}
            except ValueError as exc:
                receipt = {'provider': provider, 'model': model, 'thinking': thinking, 'status': 'BLOCKED', 'error': str(exc), 'at': now()}
            return receipt
    with ThreadPoolExecutor(max_workers=4) as pool:
        receipts = list(pool.map(check, cases))
    target = Path('output/evidence/connected-chat')
    target.mkdir(parents=True, exist_ok=True)
    (target / 'provider-probes.json').write_text(json.dumps(receipts, indent=2), encoding='utf-8')
    print(json.dumps(receipts, indent=2))


if __name__ == '__main__':
    main()
