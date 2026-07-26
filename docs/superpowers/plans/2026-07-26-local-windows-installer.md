# All for Cabal Web Local Windows Installer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full offline Windows 10/11 64-bit installer that starts All for Cabal Web on loopback, opens the browser without a visible login, preserves per-user data across upgrades, and is published only to `momozxmo/tool-cabal-local`.

**Architecture:** A Windows launcher owns runtime setup, migrations, the local Uvicorn process, and browser opening. Local mode keeps the existing session/ownership model but replaces typed login with a loopback-only, launcher-secret-protected, single-use bootstrap token. PyInstaller produces a one-directory bundle containing Python, the app, migrations, Playwright, and Chromium; Inno Setup wraps it in one offline Setup executable.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, Playwright Chromium, Tkinter, PyInstaller, Inno Setup, pytest, GitHub Releases.

## Global Constraints

- Target only Windows 10/11 64-bit.
- The installed user must not need Python, Docker, Playwright, Chromium, or terminal commands.
- Bind only to `127.0.0.1:8000`; never fall back to `0.0.0.0` or another port.
- Local mode has no visible username, password, login, logout, password-change, or user-management flow.
- Production mode keeps the existing authentication and authorization behavior unchanged.
- Passwordless Local access requires Local mode, a loopback bind, a loopback request, and the generated launcher secret.
- Keep every workspace, job, result, export, WebSocket, Aztek session, and audit record scoped to the internal local owner.
- Store mutable data only under `%LOCALAPPDATA%\AllForCabalWeb`.
- Never store or log Aztek passwords, cookies, raw storage state, pairing tokens, local launch tokens, launcher secrets, application secrets, or encryption keys.
- Never package or publish `.env`, SQLite developer databases, Chrome profiles, uploaded workbooks, logs, `dist/`, build caches, or credentials.
- The installer is fully offline after download.
- Generated Setup files are GitHub Release assets, not Git-tracked files.
- Push Local-installer commits only to `https://github.com/momozxmo/tool-cabal-local.git`; do not push them to `momozxmo/all-for-cabal`.
- Do not perform a real Aztek create without the user's separate explicit approval.

---

## File Map

- `web/settings.py`: parse explicit Local mode, runtime directory, and launcher secret.
- `web/local_access.py`: create the internal owner and issue/consume short-lived local launch tokens.
- `web/app.py`: expose loopback-only bootstrap routes and retain normal session authorization.
- `web/static/local_start.html`: consume a launch token from the URL fragment without putting it in an HTTP request URL.
- `web/static/index.html`, `web/static/console.js`, `web/static/bundles.html`, `web/static/itemcodes.html`, `web/static/events.html`, `web/static/account.html`: hide hosted-auth controls in Local mode.
- `local_app/__init__.py`: mark the Local launcher package.
- `local_app/runtime.py`: resolve `%LOCALAPPDATA%`, create/load secrets atomically, back up SQLite, and run Alembic.
- `local_app/server.py`: start/stop Uvicorn and request a one-use browser bootstrap URL.
- `local_app/launcher.py`: single-instance Tkinter controller and automatic browser opening.
- `local_app/release_verify.py`: reject forbidden packaged files and create the SHA-256 checksum.
- `local_web.spec`: PyInstaller one-directory bundle including static files, migrations, and Chromium.
- `installer/AllForCabalWeb.iss`: Inno Setup definition.
- `scripts/build_local_installer.ps1`: reproducible build pipeline.
- `requirements-build.txt`: build-only pinned tools.
- `docs/LOCAL_INSTALL.md`: team installation, update, backup, and removal instructions.
- `tests/test_local_runtime.py`, `tests/test_local_access.py`, `tests/test_local_launcher.py`, `tests/test_local_release.py`: Local-specific regression tests.

---

### Task 1: Isolated Local runtime configuration

**Files:**
- Create: `local_app/__init__.py`
- Create: `local_app/runtime.py`
- Modify: `web/settings.py`
- Create: `tests/test_local_runtime.py`

**Interfaces:**
- Produces: `RuntimePaths.for_user(local_app_data: str | None = None) -> RuntimePaths`
- Produces: `ensure_runtime_config(paths: RuntimePaths) -> dict[str, str]`
- Produces: `runtime_environment(paths: RuntimePaths, config: dict[str, str]) -> dict[str, str]`
- Produces: `backup_and_migrate(paths: RuntimePaths, environ: dict[str, str]) -> Path | None`
- Produces: `Settings.local_desktop_mode`, `Settings.local_runtime_dir`, and `Settings.local_launcher_secret`

- [ ] **Step 1: Write failing runtime path and secret tests**

```python
# tests/test_local_runtime.py
import json
from pathlib import Path

import pytest

from local_app.runtime import (
    RuntimePaths,
    backup_and_migrate,
    ensure_runtime_config,
    runtime_environment,
)


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
    assert environ['DATABASE_URL'].endswith('/AllForCabalWeb/all_for_cabal_web.db')
    assert environ['LOCAL_RUNTIME_DIR'] == str(paths.root)
```

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```powershell
python -m pytest -q tests/test_local_runtime.py
```

Expected: collection fails because `local_app.runtime` does not exist.

- [ ] **Step 3: Implement paths and atomic configuration creation**

```python
# local_app/runtime.py
from __future__ import annotations

import base64
import json
import os
import secrets
from dataclasses import dataclass
from pathlib import Path


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
        return cls(root, root / 'all_for_cabal_web.db',
                   root / 'config.json', root / 'logs', root / 'backups')


def ensure_runtime_config(paths: RuntimePaths) -> dict[str, str]:
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.logs.mkdir(exist_ok=True)
    paths.backups.mkdir(exist_ok=True)
    if paths.config.exists():
        data = json.loads(paths.config.read_text(encoding='utf-8'))
    else:
        data = {
            'app_secret_key': secrets.token_urlsafe(48),
            'aztek_encryption_key': base64.urlsafe_b64encode(
                os.urandom(32)).decode('ascii'),
            'launcher_secret': secrets.token_urlsafe(48),
        }
        temporary = paths.config.with_suffix('.tmp')
        temporary.write_text(json.dumps(data, indent=2), encoding='utf-8')
        os.replace(temporary, paths.config)
    required = {'app_secret_key', 'aztek_encryption_key', 'launcher_secret'}
    if set(data) != required or not all(isinstance(data[key], str) for key in required):
        raise ValueError('ไฟล์ตั้งค่า Local ไม่สมบูรณ์')
    return data
```

Implement `runtime_environment` with a forward-slash SQLite URL and without
writing an `.env` file. Extend `Settings` with defaulted Local fields:

```python
local_desktop_mode: bool = False
local_runtime_dir: str = ''
local_launcher_secret: str = ''
```

`Settings.from_env()` must enable Local mode only when
`LOCAL_DESKTOP_MODE=true` and `APP_ENV=local-desktop`. It must reject Local mode
when the launcher secret or runtime directory is empty.

- [ ] **Step 4: Add migration backup behavior tests**

```python
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
        backup_and_migrate(paths, {'DATABASE_URL': 'sqlite:///' + str(paths.database)})

    assert paths.database.read_bytes() == b'original database'
    assert list(paths.backups.glob('*.db'))
```

- [ ] **Step 5: Implement `backup_and_migrate`**

Use `alembic.config.Config` with absolute `script_location`, copy an existing
database to `backups/pre-migrate-YYYYMMDD-HHMMSS.db`, apply
`command.upgrade(config, 'head')`, and restore the backup with `os.replace` when
migration raises. Leave no half-written database.

- [ ] **Step 6: Run focused and settings regressions**

Run:

```powershell
python -m pytest -q tests/test_local_runtime.py tests/test_web_security.py -k "settings or migration or runtime or backup"
```

Expected: PASS.

- [ ] **Step 7: Commit Task 1**

```powershell
git add local_app/__init__.py local_app/runtime.py web/settings.py tests/test_local_runtime.py
git commit -m "feat(local): isolate runtime data and secrets"
```

---

### Task 2: Loopback-only passwordless Local bootstrap

**Files:**
- Create: `web/local_access.py`
- Create: `web/static/local_start.html`
- Modify: `web/app.py`
- Modify: `tests/conftest.py`
- Create: `tests/test_local_access.py`

**Interfaces:**
- Consumes: the three Local `Settings` fields from Task 1.
- Consumes: `AuthService.create_user` and `AuthService.create_session`.
- Produces: `LocalAccessService.ensure_owner(db: Session) -> User`
- Produces: `LocalAccessService.issue(provided_secret: str, client_host: str) -> str`
- Produces: `LocalAccessService.consume(raw_token: str, client_host: str) -> bool`
- Produces: `POST /api/local/launch`, `GET /local-start`, and `POST /api/local/session`

- [ ] **Step 1: Write failing Local access security tests**

```python
# tests/test_local_access.py
from dataclasses import replace
from fastapi.testclient import TestClient

from web import app as web_app


def _local_app(test_settings, test_database):
    settings = replace(
        test_settings,
        app_env='local-desktop',
        local_desktop_mode=True,
        local_runtime_dir='C:/Users/Test/AppData/Local/AllForCabalWeb',
        local_launcher_secret='launcher-secret-with-at-least-48-characters-0001',
        bootstrap_admin_username='',
        bootstrap_admin_password='',
    )
    return web_app.create_app(settings, test_database)


def test_local_launch_requires_loopback_and_exact_launcher_secret(
    test_settings, test_database
):
    client = TestClient(_local_app(test_settings, test_database))
    missing = client.post('/api/local/launch')
    wrong = client.post('/api/local/launch',
                        headers={'X-AFC-Launcher-Secret': 'wrong'})
    valid = client.post(
        '/api/local/launch',
        headers={'X-AFC-Launcher-Secret':
                 'launcher-secret-with-at-least-48-characters-0001'})

    assert missing.status_code == 404
    assert wrong.status_code == 404
    assert valid.status_code == 200
    assert len(valid.json()['token']) >= 32


def test_local_token_is_single_use_and_sets_strict_httponly_cookie(
    test_settings, test_database
):
    client = TestClient(_local_app(test_settings, test_database))
    token = client.post(
        '/api/local/launch',
        headers={'X-AFC-Launcher-Secret':
                 'launcher-secret-with-at-least-48-characters-0001'}
    ).json()['token']

    first = client.post('/api/local/session', json={'token': token})
    replay = client.post('/api/local/session', json={'token': token})

    assert first.status_code == 204
    cookie = first.headers['set-cookie'].lower()
    assert 'httponly' in cookie
    assert 'samesite=strict' in cookie
    assert replay.status_code == 404
    assert client.get('/api/auth/me').json()['local_mode'] is True
```

Add a direct service test with an injected clock proving expiry at 61 seconds
and a non-loopback test using `client=('192.168.1.5', 50000)` proving both
endpoints return 404.

- [ ] **Step 2: Run the access tests and verify RED**

Run:

```powershell
python -m pytest -q tests/test_local_access.py
```

Expected: collection fails because `web.local_access` and Local routes are
absent.

- [ ] **Step 3: Implement the Local access service**

```python
# web/local_access.py
from __future__ import annotations

import hmac
import ipaddress
import secrets
import threading
import time
from sqlalchemy import select

from web.models import User


def is_loopback(host: str) -> bool:
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host.casefold() == 'localhost'


class LocalAccessService:
    def __init__(self, settings, auth_service, clock=time.monotonic):
        self.settings = settings
        self.auth_service = auth_service
        self.clock = clock
        self._tokens: dict[str, float] = {}
        self._lock = threading.Lock()

    def enabled(self, client_host: str) -> bool:
        return self.settings.local_desktop_mode and is_loopback(client_host)

    def issue(self, provided_secret: str, client_host: str) -> str:
        if not self.enabled(client_host) or not hmac.compare_digest(
            provided_secret or '', self.settings.local_launcher_secret
        ):
            raise LookupError('not available')
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._tokens[token] = self.clock() + 60
        return token

    def consume(self, raw_token: str, client_host: str) -> bool:
        if not self.enabled(client_host):
            return False
        with self._lock:
            expires = self._tokens.pop(raw_token, None)
        return expires is not None and expires > self.clock()
```

`ensure_owner` creates `local.owner` through `AuthService.create_user` using a
cryptographically random password derived from the launcher secret only when
the users table is empty. It returns the existing `local.owner` on subsequent
starts and refuses to select a different user. `create_app` constructs
`LocalAccessService(resolved_settings, auth_service, monotonic_clock)` and
stores it at `application.state.local_access`.

- [ ] **Step 4: Implement Local routes without URL token leakage**

Add `LocalLaunchRequest(token: str)` to `web/app.py`.

- `POST /api/local/launch` reads `X-AFC-Launcher-Secret`; wrong, disabled, or
  non-loopback returns 404.
- `GET /local-start` serves `local_start.html` only in loopback Local mode.
- The launcher opens `http://127.0.0.1:8000/local-start#TOKEN`.
- `local_start.html` reads `location.hash`, clears the visible URL with
  `history.replaceState`, POSTs the token as JSON to `/api/local/session`, and
  redirects to `/`.
- `POST /api/local/session` consumes the token, creates a normal `WebSession`
  for the internal owner, and sets `afc_session` with HttpOnly,
  SameSite=Strict, `path=/`, and the existing TTL.

Do not enable access-log output in the packaged server. Never put a token in a
query string.

- [ ] **Step 5: Preserve production authentication tests**

Add:

```python
def test_production_does_not_expose_local_bootstrap(
    test_settings, test_database
):
    client = TestClient(web_app.create_app(test_settings, test_database))
    assert client.post('/api/local/launch',
                       headers={'X-AFC-Launcher-Secret': 'anything'}).status_code == 404
    assert client.get('/local-start').status_code == 404
    assert client.get('/').history[-1].url.path == '/login'
```

Update `_safe_user`/`GET /api/auth/me` to include
`local_mode: bool`. Keep login, logout, role, ownership, and WebSocket tests
unchanged in non-Local settings.

- [ ] **Step 6: Run Local, auth, ownership, and WebSocket tests**

Run:

```powershell
python -m pytest -q tests/test_local_access.py tests/test_web_auth.py tests/test_web_ownership.py tests/test_web_search_auth.py tests/test_web_security.py
```

Expected: PASS.

- [ ] **Step 7: Commit Task 2**

```powershell
git add web/local_access.py web/static/local_start.html web/app.py tests/conftest.py tests/test_local_access.py
git commit -m "feat(local): open loopback app without typed login"
```

---

### Task 3: Local-mode web navigation

**Files:**
- Modify: `web/static/index.html`
- Modify: `web/static/console.js`
- Modify: `web/static/bundles.html`
- Modify: `web/static/itemcodes.html`
- Modify: `web/static/events.html`
- Modify: `web/static/account.html`
- Modify: `tests/test_web_ui.py`
- Modify: `tests/test_web_calendar_ui.py`

**Interfaces:**
- Consumes: `GET /api/auth/me` response field `local_mode`.
- Produces: `applyRuntimeMode(me)` on the shared tool pages.

- [ ] **Step 1: Write failing browser tests for hidden auth controls**

Add browser-level tests that load each real page, call its runtime-mode
function with `{username: 'local.owner', role: 'admin', local_mode: true}`, and
assert:

```python
assert not page.locator('#btnLogout').is_visible()
assert not page.locator('#currentUser').is_visible()
assert page.get_by_role('link', name='เชื่อม Aztek').is_visible()
```

For `account.html`, assert the profile, password-change, and logout sections are
hidden while the Aztek pairing card remains visible.

- [ ] **Step 2: Run the browser tests and verify RED**

Run:

```powershell
python -m pytest -q tests/test_web_ui.py tests/test_web_calendar_ui.py -k "local_mode"
```

Expected: FAIL because current pages always show account identity and logout.

- [ ] **Step 3: Implement runtime-aware navigation**

Mark hosted-only elements with `data-hosted-auth` and add:

```javascript
function applyRuntimeMode(me) {
  document.querySelectorAll('[data-hosted-auth]').forEach(
    node => { node.hidden = !!me.local_mode; });
  document.querySelectorAll('[data-account-link]').forEach(
    node => { node.textContent = me.local_mode ? 'เชื่อม Aztek' : 'บัญชี / เชื่อม Aztek'; });
}
```

Call it immediately after `/api/auth/me` succeeds. Do not remove the elements
from production HTML. On the Account page, hide hosted-auth cards and leave
Aztek status, connect, and disconnect controls intact.

- [ ] **Step 4: Run browser and complete UI tests**

Run:

```powershell
python -m pytest -q tests/test_web_ui.py tests/test_web_calendar_ui.py
```

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

```powershell
git add web/static/index.html web/static/console.js web/static/bundles.html web/static/itemcodes.html web/static/events.html web/static/account.html tests/test_web_ui.py tests/test_web_calendar_ui.py
git commit -m "feat(local): hide hosted account controls"
```

---

### Task 4: Windows launcher, lifecycle, and migration safety

**Files:**
- Create: `local_app/server.py`
- Create: `local_app/launcher.py`
- Create: `tests/test_local_launcher.py`
- Modify: `requirements.txt`

**Interfaces:**
- Consumes: `RuntimePaths`, `ensure_runtime_config`, `runtime_environment`, and
  `backup_and_migrate`.
- Produces: `LocalServer.start()`, `LocalServer.open_browser()`,
  `LocalServer.restart()`, and `LocalServer.stop()`.
- Produces: `python -m local_app.launcher`.

- [ ] **Step 1: Write failing lifecycle tests**

Use a fake Uvicorn server and fake URL opener, but a real local HTTP stub for
health/token responses:

```python
def test_second_launcher_reuses_server_and_opens_new_bootstrap_url(
    runtime_paths, fake_http, monkeypatch
):
    opened = []
    monkeypatch.setattr('local_app.server.webbrowser.open', opened.append)
    fake_http.health = {'ok': True, 'product': 'all-for-cabal-local'}
    fake_http.launch_token = 'one-use-token'

    server = LocalServer(runtime_paths, {'launcher_secret': 'secret'}, http=fake_http)
    assert server.ensure_started() == 'reused'
    server.open_browser()

    assert opened == [
        'http://127.0.0.1:8000/local-start#one-use-token'
    ]
    assert fake_http.launch_headers == {'X-AFC-Launcher-Secret': 'secret'}
```

Add tests for:

- unknown process on port 8000 produces `PortInUseError`;
- startup timeout stops the partially started server;
- `restart` stops before starting;
- `stop` sets `should_exit`;
- log configuration disables Uvicorn access logs;
- browser-launch failure returns a Thai error while the server remains running.

- [ ] **Step 2: Run launcher tests and verify RED**

Run:

```powershell
python -m pytest -q tests/test_local_launcher.py
```

Expected: collection fails because `local_app.server` and
`local_app.launcher` do not exist.

- [ ] **Step 3: Implement `LocalServer`**

`LocalServer` must:

1. check `GET /api/health` and require
   `{"ok": true, "product": "all-for-cabal-local"}` before treating port 8000
   as an existing instance;
2. start `uvicorn.Server` in a non-daemon thread with host `127.0.0.1`, port
   `8000`, `access_log=False`, and a sanitized rotating file handler;
3. poll health for at most 20 seconds without blocking the Tkinter event loop;
4. issue a launch token through `POST /api/local/launch`;
5. open the fragment URL with `webbrowser.open`;
6. stop with `server.should_exit = True` and join with a bounded timeout.

The `/api/health` response includes the product marker only in Local mode.

- [ ] **Step 4: Implement the Tkinter controller**

`local_app/launcher.py` must:

- call `RuntimePaths.for_user`, `ensure_runtime_config`,
  `runtime_environment`, and `backup_and_migrate` before importing
  `web.app`;
- apply the returned environment to `os.environ` only in the launcher process;
- use a Windows named mutex `Local\AllForCabalWebLauncher` through `ctypes`;
- when the mutex already exists, call the running server's launch endpoint,
  open a new browser tab, and exit;
- show Thai state text plus `เปิดหน้าเว็บ`, `เริ่มใหม่`, and `ปิดโปรแกรม`;
- ask once before stopping on window close;
- never display, print, or log secret values.

- [ ] **Step 5: Run launcher and complete regression tests**

Run:

```powershell
python -m pytest -q tests/test_local_launcher.py tests/test_local_runtime.py tests/test_local_access.py
python -m pytest -q
```

Expected: the focused tests pass and the complete suite has zero failures.

- [ ] **Step 6: Commit Task 4**

```powershell
git add local_app/server.py local_app/launcher.py tests/test_local_launcher.py requirements.txt web/app.py
git commit -m "feat(local): add Windows web launcher"
```

---

### Task 5: Reproducible offline bundle and installer

**Files:**
- Create: `requirements-build.txt`
- Create: `local_web.spec`
- Create: `installer/AllForCabalWeb.iss`
- Create: `scripts/build_local_installer.ps1`
- Create: `local_app/release_verify.py`
- Create: `tests/test_local_release.py`
- Modify: `.gitignore`
- Modify: `.dockerignore`

**Interfaces:**
- Produces: `python -m local_app.release_verify PATH_TO_PACKAGE`
- Produces: `artifacts/All for Cabal Web Setup-VERSION.exe`
- Produces: `artifacts/All for Cabal Web Setup-VERSION.exe.sha256`

- [ ] **Step 1: Write failing artifact-verification tests**

```python
# tests/test_local_release.py
from pathlib import Path
import pytest

from local_app.release_verify import verify_tree, write_checksum


def test_release_verifier_rejects_private_runtime_files(tmp_path):
    package = tmp_path / 'package'
    package.mkdir()
    (package / 'web').mkdir()
    (package / 'web' / 'app.py').write_text('safe', encoding='utf-8')
    (package / 'all_for_cabal_web.db').write_bytes(b'private')

    with pytest.raises(ValueError, match='all_for_cabal_web.db'):
        verify_tree(package)


def test_release_verifier_accepts_app_and_writes_sha256(tmp_path):
    package = tmp_path / 'package'
    package.mkdir()
    (package / 'All for Cabal Web.exe').write_bytes(b'installer')
    verify_tree(package)
    checksum = write_checksum(package / 'All for Cabal Web.exe')
    assert checksum.read_text(encoding='ascii').endswith(
        ' *All for Cabal Web.exe\n')
```

- [ ] **Step 2: Run the verifier tests and verify RED**

Run:

```powershell
python -m pytest -q tests/test_local_release.py
```

Expected: collection fails because `local_app.release_verify` does not exist.

- [ ] **Step 3: Implement release verification**

Reject case-insensitive names matching:

```python
FORBIDDEN_NAMES = {
    '.env', 'all_for_cabal_web.db', 'all_for_cabal_web_dev.db',
    '.cabal_chrome_profile', 'config.json',
}
FORBIDDEN_SUFFIXES = {'.db', '.sqlite', '.sqlite3', '.xlsx', '.xlsm', '.log'}
```

Also reject any path component named `.git`, `.worktrees`, `dist`, `build`,
`__pycache__`, or `.pytest_cache`. Compute SHA-256 by streaming 1 MiB chunks.

- [ ] **Step 4: Define the PyInstaller one-directory bundle**

`local_web.spec` must:

- use `local_app/launcher.py` as the entry point;
- use `EXE(..., console=False, icon='icon.ico')`;
- finish with `COLLECT` for a one-directory build;
- include `web/static`, `alembic`, `alembic.ini`, and `icon.ico`;
- include packages required by FastAPI, Uvicorn, SQLAlchemy, Alembic,
  cryptography, argon2, openpyxl, and Playwright;
- include the Chromium directory created under
  `build-cache/ms-playwright`;
- set the packaged browser path before Playwright imports.

Pin build tools in `requirements-build.txt`:

```text
pyinstaller==6.15.*
pytest==8.4.*
```

- [ ] **Step 5: Define the Inno Setup installer**

`installer/AllForCabalWeb.iss` must use:

```ini
[Setup]
AppId={{6B5A3461-9A4C-4D08-A72A-6F7426F22C91}
AppName=All for Cabal Web
DefaultDirName={autopf}\All for Cabal Web
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\artifacts
PrivilegesRequired=lowest
Compression=lzma2/ultra64
SolidCompression=yes

[Run]
Filename: "{app}\All for Cabal Web.exe"; Flags: nowait postinstall skipifsilent
```

Copy the full PyInstaller directory, create Start Menu and optional Desktop
shortcuts, and do not add `%LOCALAPPDATA%\AllForCabalWeb` to `[UninstallDelete]`.

- [ ] **Step 6: Implement the PowerShell build pipeline**

`scripts/build_local_installer.ps1` must stop on error and perform:

```powershell
python -m pip install -r requirements.txt -r requirements-build.txt
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $PSScriptRoot '..\build-cache\ms-playwright'
python -m playwright install chromium
python -m pytest -q
pyinstaller --noconfirm --clean local_web.spec
python -m local_app.release_verify "dist\All for Cabal Web"
& $iscc "installer\AllForCabalWeb.iss"
python -m local_app.release_verify "artifacts"
```

Resolve `ISCC.exe` from the standard Inno Setup 6 installation path and fail
with a Thai installation instruction when absent. Do not download or silently
install Inno Setup from the build script.

- [ ] **Step 7: Harden ignore files**

Add `artifacts/`, `build-cache/`, `*.iss.sig`, and local runtime directories to
`.gitignore` and `.dockerignore`. Verify:

```powershell
git check-ignore -v .env all_for_cabal_web_dev.db artifacts build-cache
```

- [ ] **Step 8: Run release and complete tests**

Run:

```powershell
python -m pytest -q tests/test_local_release.py
python -m pytest -q
git diff --check
```

Expected: all commands succeed.

- [ ] **Step 9: Commit Task 5**

```powershell
git add requirements-build.txt local_web.spec installer/AllForCabalWeb.iss scripts/build_local_installer.ps1 local_app/release_verify.py tests/test_local_release.py .gitignore .dockerignore
git commit -m "build(local): package offline Windows installer"
```

---

### Task 6: Build, install, upgrade, and clean-machine verification

**Files:**
- Create: `docs/LOCAL_INSTALL.md`
- Modify: `README.md`
- Generated, ignored: `artifacts/All for Cabal Web Setup-0.1.0.exe`
- Generated, ignored: `artifacts/All for Cabal Web Setup-0.1.0.exe.sha256`

**Interfaces:**
- Consumes: the completed build pipeline from Task 5.
- Produces: a verified installer and team-facing instructions.

- [ ] **Step 1: Write the team installation document**

Document exactly:

1. download the Setup file and matching `.sha256`;
2. verify with
   `Get-FileHash ".\All for Cabal Web Setup-0.1.0.exe" -Algorithm SHA256`;
3. install and leave `เปิด All for Cabal Web` checked;
4. use the controller buttons;
5. connect Aztek without entering an Aztek password into All for Cabal;
6. update by installing the newer Setup over the existing version;
7. back up `%LOCALAPPDATA%\AllForCabalWeb`;
8. uninstall behavior and the explicit manual data-removal path.

Add a short Local installer section to `README.md` linking to this document.

- [ ] **Step 2: Build the complete offline installer**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_local_installer.ps1
```

Expected:

- PyInstaller succeeds;
- Inno Setup succeeds;
- the release verifier finds no forbidden files;
- Setup and SHA-256 files exist under `artifacts/`.

- [ ] **Step 3: Verify on a clean Windows 10/11 64-bit VM**

Use a VM with Python, Docker, Playwright, and developer Chrome profiles absent.
Disconnect network access during installation and first application start.

Verify:

- install completes;
- shortcut opens the controller and Item Finder without login;
- only `127.0.0.1:8000` listens;
- second shortcut invocation opens another authenticated tab without a second
  server;
- closing the controller stops port 8000;
- reconnecting network permits Bookmarklet pairing and preview;
- no Aztek password is requested or stored.

Do not press a real create button.

- [ ] **Step 4: Verify upgrade preservation**

On the VM:

1. create an imported workspace and pair Aztek;
2. close the app;
3. install a second build with a higher version over the first;
4. reopen;
5. confirm workspace/history and Aztek connection remain;
6. confirm a pre-migration backup exists;
7. uninstall and confirm `%LOCALAPPDATA%\AllForCabalWeb` remains.

- [ ] **Step 5: Record release evidence**

Add a table to `docs/LOCAL_INSTALL.md` with:

- Windows edition/build;
- installer version;
- Setup SHA-256;
- install/offline start/second launch/stop/upgrade/uninstall results;
- explicit note that real Aztek create was not tested.

- [ ] **Step 6: Run final verification and commit documentation**

Run:

```powershell
python -m pytest -q
git diff --check
git status --short
```

Expected: zero test failures, clean diff check, and only intended documentation
changes.

Commit:

```powershell
git add docs/LOCAL_INSTALL.md README.md
git commit -m "docs(local): add installer and upgrade guide"
```

---

### Task 7: Publish only to the separate GitHub repository

**Files:**
- No source changes required.
- Generated, ignored release assets under `artifacts/`.

**Interfaces:**
- Consumes: clean Git history and verified artifacts from Task 6.
- Produces: `momozxmo/tool-cabal-local` `main` and GitHub Release `v0.1.0`.

- [ ] **Step 1: Inspect authentication and the destination without writing**

Run:

```powershell
gh auth status
git ls-remote https://github.com/momozxmo/tool-cabal-local.git
git remote -v
```

Expected: GitHub authentication is valid. Record whether the destination is
empty. Do not force-push over an existing branch.

- [ ] **Step 2: Add a separate remote**

Run:

```powershell
git remote add local-release https://github.com/momozxmo/tool-cabal-local.git
git remote get-url local-release
```

Expected: only `local-release` points to `tool-cabal-local`; `origin` remains
`momozxmo/all-for-cabal`.

- [ ] **Step 3: Run the pre-push privacy gate**

Run:

```powershell
git status --short
git diff --check
git ls-files | rg -i "(^|/)(\.env|.*\.(db|sqlite|sqlite3)|\.cabal_chrome_profile|dist|artifacts|build-cache)(/|$)"
python -m pytest -q
```

Expected: clean worktree, clean diff, no forbidden tracked paths, and zero test
failures.

- [ ] **Step 4: Push source to the separate repository**

If the destination has no `main` branch:

```powershell
git push -u local-release HEAD:main
```

If it already has commits, fetch and inspect first:

```powershell
git fetch local-release main
git log --oneline --left-right HEAD...local-release/main
```

Integrate existing destination history without `--force`, rerun Task 7 Step 3,
then push `HEAD:main`.

- [ ] **Step 5: Create the verified GitHub Release**

Run:

```powershell
gh release create v0.1.0 `
  "artifacts\All for Cabal Web Setup-0.1.0.exe" `
  "artifacts\All for Cabal Web Setup-0.1.0.exe.sha256" `
  --repo momozxmo/tool-cabal-local `
  --title "All for Cabal Web Local v0.1.0" `
  --notes-file docs\LOCAL_INSTALL.md
```

Expected: the release page contains exactly the Setup executable and checksum.

- [ ] **Step 6: Verify the published download**

Download both release assets into a new temporary directory, recompute SHA-256,
and compare it to the published checksum. Report the repository URL, release
URL, commit hash, artifact size, and SHA-256 to the user.
