import pytest

from web.settings import Settings


PRODUCTION_SETTINGS = {
    'APP_SECRET_KEY': 'app-secret',
    'AZTEK_SESSION_ENCRYPTION_KEY': 'encryption-key',
    'BOOTSTRAP_ADMIN_USERNAME': 'admin',
    'BOOTSTRAP_ADMIN_PASSWORD': 'password',
}


def configure_production(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'production')
    for name, value in PRODUCTION_SETTINGS.items():
        monkeypatch.setenv(name, value)


def test_settings_default_to_local_sqlite(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'development')
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with pytest.warns(RuntimeWarning, match='sessions will not survive restart'):
        settings = Settings.from_env()
    assert settings.database_url == 'sqlite:///./all_for_cabal_web.db'
    assert settings.browser_concurrency == 1


@pytest.mark.parametrize('missing_setting', PRODUCTION_SETTINGS)
def test_production_rejects_each_missing_secret(monkeypatch, missing_setting):
    configure_production(monkeypatch)
    monkeypatch.delenv(missing_setting)
    with pytest.raises(ValueError, match=missing_setting):
        Settings.from_env()


def test_production_forces_secure_session_cookie(monkeypatch):
    configure_production(monkeypatch)
    monkeypatch.setenv('SESSION_COOKIE_SECURE', 'false')
    settings = Settings.from_env()
    assert settings.session_cookie_secure is True


def test_development_warns_about_process_local_secrets(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'development')
    with pytest.warns(RuntimeWarning, match='sessions will not survive restart'):
        Settings.from_env()


def test_malformed_browser_concurrency_is_rejected(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'development')
    monkeypatch.setenv('BROWSER_CONCURRENCY', 'many')
    with pytest.warns(RuntimeWarning, match='sessions will not survive restart'):
        with pytest.raises(ValueError, match='BROWSER_CONCURRENCY must be an integer'):
            Settings.from_env()
