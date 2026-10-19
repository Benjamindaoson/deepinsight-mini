import pytest


def test_linux_vault_roundtrip_wrong_key_and_no_plaintext(tmp_path, monkeypatch):
    from cryptography.fernet import Fernet
    from app.secrets import protect
    key = Fernet.generate_key().decode()
    monkeypatch.setenv('MINI_VAULT_KEY', key)
    ciphertext = protect(b'private-test-only', platform='posix')
    assert b'private-test-only' not in ciphertext
    assert protect(ciphertext, decrypt=True, platform='posix') == b'private-test-only'
    monkeypatch.setenv('MINI_VAULT_KEY', Fernet.generate_key().decode())
    with pytest.raises(ValueError):
        protect(ciphertext, decrypt=True, platform='posix')
    monkeypatch.delenv('MINI_VAULT_KEY')
    with pytest.raises(ValueError):
        protect(b'private', platform='posix')


def test_seed_initialization_does_not_overwrite_existing_database(tmp_path):
    from app.railway_runtime import initialize_seed
    from app.database import Store
    seed = tmp_path / 'seed'
    seed.mkdir()
    original = Store(seed / 'market.sqlite3')
    original.set_setting('seed-marker', 'public-test-fixture')
    persistent = tmp_path / 'volume'
    initialize_seed(seed, persistent)
    migrated = Store(persistent / 'data/market.sqlite3')
    assert migrated.setting('seed-marker') == 'public-test-fixture'
    migrated.set_setting('seed-marker', 'persistent-new-value')
    initialize_seed(seed, persistent)
    assert migrated.setting('seed-marker') == 'persistent-new-value'


def test_resource_metrics_are_safe_and_numeric():
    from app.railway_runtime import resource_metrics
    result = resource_metrics()
    assert result['process_rss_bytes'] >= 0
    assert 'environ' not in str(result)
