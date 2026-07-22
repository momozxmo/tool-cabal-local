import pytest
from sqlalchemy import inspect

from web.db import Database
from web.models import User
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


def test_schema_creates_all_security_and_job_tables(test_database):
    names = set(inspect(test_database.engine).get_table_names())
    assert {
        'users', 'web_sessions', 'pairing_tokens', 'aztek_sessions',
        'workspaces', 'pending_imports', 'jobs', 'audit_logs',
    } <= names


def test_schema_enforces_identity_and_ownership_constraints(test_database):
    schema = inspect(test_database.engine)

    def foreign_keys(table_name):
        return {
            (tuple(item['constrained_columns']), item['referred_table'],
             tuple(item['referred_columns']))
            for item in schema.get_foreign_keys(table_name)
        }

    def unique_columns(table_name):
        constraints = {
            tuple(item['column_names'])
            for item in schema.get_unique_constraints(table_name)
        }
        indexes = {
            tuple(item['column_names'])
            for item in schema.get_indexes(table_name)
            if item['unique']
        }
        return constraints | indexes

    assert ('username',) in unique_columns('users')
    assert ('token_hash',) in unique_columns('web_sessions')
    assert ('token_hash',) in unique_columns('pairing_tokens')
    assert ('user_id',) in unique_columns('aztek_sessions')

    assert (('user_id',), 'users', ('id',)) in foreign_keys('web_sessions')
    assert (('user_id',), 'users', ('id',)) in foreign_keys('pairing_tokens')
    assert (('user_id',), 'users', ('id',)) in foreign_keys('aztek_sessions')
    assert (('owner_user_id',), 'users', ('id',)) in foreign_keys('workspaces')
    assert (('owner_user_id',), 'users', ('id',)) in foreign_keys('pending_imports')
    assert (('workspace_id',), 'workspaces', ('id',)) in foreign_keys('pending_imports')
    assert (('user_id',), 'users', ('id',)) in foreign_keys('jobs')
    assert (('workspace_id',), 'workspaces', ('id',)) in foreign_keys('jobs')
    assert (('user_id',), 'users', ('id',)) in foreign_keys('audit_logs')
    audit_user_id = next(
        column for column in schema.get_columns('audit_logs')
        if column['name'] == 'user_id'
    )
    assert audit_user_id['nullable'] is True


def test_database_session_commits_and_rolls_back(test_database):
    committed_id = '2' * 32
    rolled_back_id = '3' * 32

    with test_database.session() as session:
        session.add(User(
            id=committed_id, username='committed', password_hash='hash'))

    with test_database.session() as session:
        assert session.get(User, committed_id) is not None

    with pytest.raises(RuntimeError, match='trigger rollback'):
        with test_database.session() as session:
            session.add(User(
                id=rolled_back_id, username='rolled-back', password_hash='hash'))
            session.flush()
            raise RuntimeError('trigger rollback')

    with test_database.session() as session:
        assert session.get(User, rolled_back_id) is None


def test_timestamps_round_trip_as_utc_aware_values(db_session):
    db_session.add(User(id='1' * 32, username='member', password_hash='hash'))
    db_session.flush()
    db_session.expunge_all()

    user = db_session.get(User, '1' * 32)
    assert user is not None
    assert user.created_at.tzinfo is not None
    assert user.created_at.utcoffset().total_seconds() == 0
