import pytest

from web.settings import Settings


def test_settings_default_to_local_sqlite(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    settings = Settings.from_env()
    assert settings.database_url == 'sqlite:///./all_for_cabal_web.db'
    assert settings.browser_concurrency == 1


def test_production_rejects_missing_secrets(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.delenv('APP_SECRET_KEY', raising=False)
    with pytest.raises(ValueError, match='APP_SECRET_KEY'):
        Settings.from_env()
