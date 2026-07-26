from __future__ import annotations

import base64
import json
import os
import secrets
import shutil
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config


@dataclass(frozen=True)
class RuntimePaths:
    root: Path
    database: Path
    config: Path
    logs: Path
    backups: Path

    @classmethod
    def for_user(cls, local_app_data: str | None = None) -> 'RuntimePaths':
        base = Path(local_app_data or os.environ['LOCALAPPDATA'])
        root = base / 'AllForCabalWeb'
        return cls(
            root=root,
            database=root / 'all_for_cabal_web.db',
            config=root / 'config.json',
            logs=root / 'logs',
            backups=root / 'backups',
        )


def ensure_runtime_config(paths: RuntimePaths) -> dict[str, str]:
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.logs.mkdir(exist_ok=True)
    paths.backups.mkdir(exist_ok=True)
    if paths.config.exists():
        try:
            data = json.loads(paths.config.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError('ไฟล์ตั้งค่า Local อ่านไม่ได้') from exc
    else:
        data = {
            'app_secret_key': secrets.token_urlsafe(48),
            'aztek_encryption_key': base64.urlsafe_b64encode(
                os.urandom(32)).decode('ascii'),
            'launcher_secret': secrets.token_urlsafe(48),
        }
        temporary = paths.config.with_suffix('.tmp')
        try:
            temporary.write_text(
                json.dumps(data, indent=2, sort_keys=True),
                encoding='utf-8',
            )
            os.replace(temporary, paths.config)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
    required = {
        'app_secret_key',
        'aztek_encryption_key',
        'launcher_secret',
    }
    if (
        set(data) != required
        or not all(isinstance(data[key], str) and data[key] for key in required)
    ):
        raise ValueError('ไฟล์ตั้งค่า Local ไม่สมบูรณ์')
    return data


def runtime_environment(
    paths: RuntimePaths,
    config: dict[str, str],
) -> dict[str, str]:
    return {
        'APP_ENV': 'local-desktop',
        'LOCAL_DESKTOP_MODE': 'true',
        'LOCAL_RUNTIME_DIR': str(paths.root),
        'LOCAL_LAUNCHER_SECRET': config['launcher_secret'],
        'DATABASE_URL': 'sqlite:///' + paths.database.as_posix(),
        'APP_SECRET_KEY': config['app_secret_key'],
        'AZTEK_SESSION_ENCRYPTION_KEY': config['aztek_encryption_key'],
        'SESSION_COOKIE_SECURE': 'false',
        'BROWSER_CONCURRENCY': '1',
        'BOOTSTRAP_ADMIN_USERNAME': '',
        'BOOTSTRAP_ADMIN_PASSWORD': '',
    }


def resource_root() -> Path:
    bundled = getattr(sys, '_MEIPASS', '')
    if bundled:
        return Path(bundled)
    return Path(__file__).resolve().parents[1]


@contextmanager
def _temporary_environment(values: dict[str, str]):
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def backup_and_migrate(
    paths: RuntimePaths,
    environ: dict[str, str],
) -> Path | None:
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.logs.mkdir(exist_ok=True)
    paths.backups.mkdir(exist_ok=True)
    existed = paths.database.exists()
    backup = None
    if existed:
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        backup = paths.backups / f'pre-migrate-{stamp}.db'
        shutil.copy2(paths.database, backup)

    root = resource_root()
    alembic_config = Config(str(root / 'alembic.ini'))
    alembic_config.set_main_option(
        'script_location', str(root / 'alembic'))
    try:
        with _temporary_environment(environ):
            command.upgrade(alembic_config, 'head')
    except Exception:
        if backup is not None:
            shutil.copy2(backup, paths.database)
        elif paths.database.exists():
            paths.database.unlink()
        raise
    return backup
