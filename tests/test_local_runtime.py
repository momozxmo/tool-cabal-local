from __future__ import annotations

import json

import pytest

from local_app.runtime import (
    RuntimePaths,
    backup_and_migrate,
    ensure_runtime_config,
    runtime_environment,
)
from web.settings import Settings


def test_runtime_paths_stay_under_supplied_local_app_data(tmp_path):
    paths = RuntimePaths.for_user(str(tmp_path))

    assert paths.root == tmp_path / 'AllForCabalWeb'
    assert paths.database == paths.root / 'all_for_cabal_web.db'
    assert paths.config == paths.root / 'config.json'
    assert paths.logs == paths.root / 'logs'
    assert paths.backups == paths.root / 'backups'


def test_first_run_generates_stable_secrets_and_sqlite_url(tmp_path):
    paths = RuntimePaths.for_user(str(tmp_path))

    first = ensure_runtime_config(paths)
    second = ensure_runtime_config(paths)

    assert first == second
    assert len(first['app_secret_key']) >= 48
    assert len(first['launcher_secret']) >= 48
    assert first['aztek_encryption_key'] != first['app_secret_key']
    assert json.loads(paths.config.read_text(encoding='utf-8')) == first

    environ = runtime_environment(paths, first)
    assert environ['APP_ENV'] == 'local-desktop'
    assert environ['LOCAL_DESKTOP_MODE'] == 'true'
    assert environ['DATABASE_URL'].endswith(
        '/AllForCabalWeb/all_for_cabal_web.db')
    assert environ['LOCAL_RUNTIME_DIR'] == str(paths.root)
    assert environ['APP_SECRET_KEY'] == first['app_secret_key']
    assert environ['AZTEK_SESSION_ENCRYPTION_KEY'] == (
        first['aztek_encryption_key'])
    assert environ['LOCAL_LAUNCHER_SECRET'] == first['launcher_secret']


@pytest.mark.parametrize(
    ('name', 'value'),
    [
        ('LOCAL_RUNTIME_DIR', ''),
        ('LOCAL_LAUNCHER_SECRET', ''),
    ],
)
def test_local_settings_require_runtime_directory_and_launcher_secret(
    monkeypatch, name, value
):
    values = {
        'APP_ENV': 'local-desktop',
        'LOCAL_DESKTOP_MODE': 'true',
        'LOCAL_RUNTIME_DIR': 'C:/Local/AllForCabalWeb',
        'LOCAL_LAUNCHER_SECRET': 'x' * 48,
        'APP_SECRET_KEY': 'a' * 48,
        'AZTEK_SESSION_ENCRYPTION_KEY':
            'a2tra2tra2tra2tra2tra2tra2tra2tra2tra2tra2s=',
    }
    values[name] = value
    for key, setting in values.items():
        monkeypatch.setenv(key, setting)

    with pytest.raises(ValueError, match=name):
        Settings.from_env()


def test_local_settings_cannot_be_enabled_under_another_environment(
    monkeypatch,
):
    monkeypatch.setenv('APP_ENV', 'development')
    monkeypatch.setenv('LOCAL_DESKTOP_MODE', 'true')
    monkeypatch.setenv('LOCAL_RUNTIME_DIR', 'C:/Local/AllForCabalWeb')
    monkeypatch.setenv('LOCAL_LAUNCHER_SECRET', 'x' * 48)

    with pytest.raises(ValueError, match='APP_ENV=local-desktop'):
        Settings.from_env()


def test_backup_and_migrate_restores_database_when_migration_fails(
    tmp_path, monkeypatch
):
    paths = RuntimePaths.for_user(str(tmp_path))
    paths.root.mkdir(parents=True)
    paths.database.write_bytes(b'original database')

    def fail(_config, _revision):
        paths.database.write_bytes(b'partially migrated')
        raise RuntimeError('migration failed')

    monkeypatch.setattr('local_app.runtime.command.upgrade', fail)

    with pytest.raises(RuntimeError, match='migration failed'):
        backup_and_migrate(
            paths,
            {'DATABASE_URL': 'sqlite:///' + paths.database.as_posix()},
        )

    assert paths.database.read_bytes() == b'original database'
    backups = list(paths.backups.glob('pre-migrate-*.db'))
    assert len(backups) == 1
    assert backups[0].read_bytes() == b'original database'


def test_backup_and_migrate_does_not_back_up_a_missing_database(
    tmp_path, monkeypatch
):
    paths = RuntimePaths.for_user(str(tmp_path))
    calls = []
    monkeypatch.setattr(
        'local_app.runtime.command.upgrade',
        lambda config, revision: calls.append((config, revision)),
    )

    backup = backup_and_migrate(
        paths,
        {'DATABASE_URL': 'sqlite:///' + paths.database.as_posix()},
    )

    assert backup is None
    assert len(calls) == 1
    assert calls[0][1] == 'head'
    assert paths.backups.is_dir()
