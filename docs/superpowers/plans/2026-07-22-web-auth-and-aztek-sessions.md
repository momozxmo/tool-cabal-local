# Web Auth and Per-User Aztek Sessions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เพิ่มบัญชีล็อกอินเว็บที่ admin จัดการ, session Aztek แยกต่อผู้ใช้ผ่าน Chrome Extension, resource ownership และ audit log ให้ Item Finder Web

**Architecture:** FastAPI ใช้ SQLAlchemy repository กับ SQLite ตอนพัฒนาและ PostgreSQL ผ่าน `DATABASE_URL` ตอน deploy; web session เป็น opaque HttpOnly cookie ที่ฐานข้อมูลเก็บเฉพาะ token hash. Extension ส่ง Aztek storage state ด้วย one-time pairing token และ backend เข้ารหัสก่อนเก็บ; Playwright สร้าง non-persistent context จาก session ของเจ้าของ job.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, argon2-cffi, cryptography AES-GCM, Playwright, SQLite/PostgreSQL, Chrome Extension Manifest V3, pytest

## Global Constraints

- ไม่มี public signup; admin เป็นผู้สร้างบัญชี `admin` และ `member`
- ห้ามเก็บหรือส่งรหัสผ่าน Aztek
- ห้าม log password, web-session token, pairing token, Aztek cookie หรือ storage state ดิบ
- Pairing token หมดอายุใน 5 นาทีและใช้ได้ครั้งเดียว
- Production cookie ต้องเป็น `HttpOnly`, `Secure`, `SameSite=Lax`
- ทุก workspace, job, result, export และ WebSocket ต้องตรวจ `owner_user_id` ฝั่ง server
- Server ห้ามใช้ `.cabal_chrome_profile` หรือ persistent Chrome profile ร่วมกัน
- Browser concurrency เริ่มที่ `1`
- Local ใช้ SQLite; production ใช้ Supabase หรือ Neon PostgreSQL ผ่าน `DATABASE_URL`
- Desktop tkinter ต้องทำงานต่อได้และชุดทดสอบเดิมต้องผ่าน
- ห้าม stage/commit `dist/`, `.cabal_chrome_profile/`, `.env`, local database, encryption keys หรือ credentials

---

## File map

**Create**

- `web/settings.py` — อ่านและ validate environment configuration
- `web/db.py` — SQLAlchemy engine/session/base และ test database wiring
- `web/models.py` — ORM models ทั้งหมด
- `web/security.py` — password/token/encryption primitives
- `web/auth_service.py` — login, web session, bootstrap admin และ dependencies
- `web/audit.py` — sanitized audit writer/query
- `web/workspaces.py` — persistent owner-scoped workspace/pending-import repository
- `web/aztek_sessions.py` — pairing และ encrypted storage-state service
- `web/search_coordinator.py` — concurrency gate, jobs และ per-user search lifecycle
- `web/static/login.html` — login UI
- `web/static/account.html` — account + connect Aztek UI
- `web/static/admin.html` — users + audit UI
- `extension/manifest.json`, `extension/popup.html`, `extension/popup.js`, `extension/content.js`, `extension/config.js` — private MV3 extension
- `alembic.ini`, `alembic/env.py`, `alembic/versions/<revision>_auth_and_sessions.py` — production migrations
- `tests/conftest.py` — isolated app/database/auth fixtures
- `tests/test_web_security.py`, `tests/test_web_auth.py`, `tests/test_web_ownership.py`, `tests/test_web_admin_audit.py`, `tests/test_aztek_pairing.py`, `tests/test_web_search_auth.py`, `tests/test_extension_contract.py`
- `docs/deploy-render.md`, `docs/install-extension.md`

**Modify**

- `.gitignore` — ignore runtime browser/database/secret files
- `requirements.txt` — database/auth/encryption dependencies
- `web/app.py` — app factory, routers, auth guards และ owner-scoped endpoints
- `web/search_runner.py` — expose non-persistent `run(storage_state)`; never alter desktop `_auto`
- `web/static/index.html` — user/status bar, auth-aware fetch, reconnect flow
- `tests/test_web_api.py`, `tests/test_web_ui.py`, `tests/test_web_runner.py` — use authenticated fixtures and assert new contracts

---

### Task 1: Runtime configuration, dependencies, and secret exclusions

**Files:**
- Create: `web/settings.py`
- Modify: `requirements.txt`
- Modify: `.gitignore`
- Test: `tests/test_web_security.py`

**Interfaces:**
- Produces: `Settings.from_env() -> Settings`, `settings.database_url`, `settings.session_cookie_secure`, `settings.browser_concurrency`

- [ ] **Step 1: Write failing settings tests**

```python
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
```

- [ ] **Step 2: Run the tests and verify failure**

Run: `python -B -m pytest tests/test_web_security.py -q`

Expected: FAIL because `web.settings` does not exist.

- [ ] **Step 3: Add pinned dependency ranges and settings implementation**

Add to `requirements.txt`:

```text
SQLAlchemy>=2.0,<3
alembic>=1.13,<2
argon2-cffi>=23,<26
cryptography>=42,<46
psycopg[binary]>=3.1,<4
```

Implement immutable settings with these exact fields; import `base64`, `os`, and `secrets` from the standard library:

```python
@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    app_secret_key: str
    aztek_encryption_key: str
    bootstrap_admin_username: str
    bootstrap_admin_password: str
    session_cookie_secure: bool
    session_ttl_seconds: int = 604800
    pairing_ttl_seconds: int = 300
    browser_concurrency: int = 1
    aztek_origin: str = 'https://aztek-tools.combo-interactive.com'

    @classmethod
    def from_env(cls) -> 'Settings':
        app_env = os.getenv('APP_ENV', 'development').strip().lower()
        production = app_env == 'production'
        app_secret = os.getenv('APP_SECRET_KEY', '').strip()
        encryption_key = os.getenv('AZTEK_SESSION_ENCRYPTION_KEY', '').strip()
        admin_user = os.getenv('BOOTSTRAP_ADMIN_USERNAME', '').strip()
        admin_password = os.getenv('BOOTSTRAP_ADMIN_PASSWORD', '')
        if production:
            missing = [name for name, value in (
                ('APP_SECRET_KEY', app_secret),
                ('AZTEK_SESSION_ENCRYPTION_KEY', encryption_key),
                ('BOOTSTRAP_ADMIN_USERNAME', admin_user),
                ('BOOTSTRAP_ADMIN_PASSWORD', admin_password),
            ) if not value]
            if missing:
                raise ValueError('missing production settings: ' + ', '.join(missing))
        return cls(
            app_env=app_env,
            database_url=os.getenv('DATABASE_URL', 'sqlite:///./all_for_cabal_web.db'),
            app_secret_key=app_secret or secrets.token_urlsafe(48),
            aztek_encryption_key=encryption_key or base64.urlsafe_b64encode(
                os.urandom(32)).decode('ascii'),
            bootstrap_admin_username=admin_user,
            bootstrap_admin_password=admin_password,
            session_cookie_secure=os.getenv(
                'SESSION_COOKIE_SECURE', 'true' if production else 'false'
            ).lower() == 'true',
            browser_concurrency=max(1, int(os.getenv('BROWSER_CONCURRENCY', '1'))),
        )
```

Production must reject empty `APP_SECRET_KEY`, `AZTEK_SESSION_ENCRYPTION_KEY`, bootstrap username, and bootstrap password. Local mode may generate process-local secrets only for tests/dev and must emit a warning that sessions will not survive restart.

- [ ] **Step 4: Protect runtime files**

Append exactly these patterns to `.gitignore`:

```gitignore
.cabal_chrome_profile/
.env
*.db
*.sqlite
*.sqlite3
extension/config.local.js
```

Run: `git status --short`

Expected: `.cabal_chrome_profile/` no longer appears; existing `dist/` remains ignored and untouched.

- [ ] **Step 5: Run tests and commit**

Run: `python -B -m pytest tests/test_web_security.py -q`

Expected: PASS.

```powershell
git add .gitignore requirements.txt web/settings.py tests/test_web_security.py
git commit -m "chore(web): add secure runtime configuration"
```

---

### Task 2: Database schema and migration foundation

**Files:**
- Create: `web/db.py`
- Create: `web/models.py`
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/versions/<revision>_auth_and_sessions.py`
- Create: `tests/conftest.py`
- Test: `tests/test_web_security.py`

**Interfaces:**
- Produces: `Database(settings)`, `Database.session()`, `Base`, ORM classes `User`, `WebSession`, `PairingToken`, `AztekSession`, `WorkspaceRecord`, `PendingImportRecord`, `Job`, `AuditLog`

- [ ] **Step 1: Write a failing schema test**

```python
def test_schema_creates_all_security_and_job_tables(test_database):
    names = set(inspect(test_database.engine).get_table_names())
    assert {'users', 'web_sessions', 'pairing_tokens', 'aztek_sessions',
            'workspaces', 'pending_imports', 'jobs', 'audit_logs'} <= names
```

- [ ] **Step 2: Verify failure**

Run: `python -B -m pytest tests/test_web_security.py::test_schema_creates_all_security_and_job_tables -q`

Expected: FAIL because `Database` and models do not exist.

- [ ] **Step 3: Implement database wiring and models**

Use SQLAlchemy 2 typed models. Required invariants:

```python
class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(16), default='member')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class WorkspaceRecord(Base):
    __tablename__ = 'workspaces'
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    mode: Mapped[str] = mapped_column(String(16))
    filename: Mapped[str] = mapped_column(Text, default='')
    criteria: Mapped[list] = mapped_column(JSON, default=list)
    occurrences: Mapped[list] = mapped_column(JSON, default=list)
    group_meta: Mapped[dict] = mapped_column(JSON, default=dict)
    skipped: Mapped[list] = mapped_column(JSON, default=list)
    results: Mapped[list] = mapped_column(JSON, default=list)
    not_found: Mapped[list] = mapped_column(JSON, default=list)
    game: Mapped[str] = mapped_column(String(80), default='')
```

`WebSession.token_hash` and `PairingToken.token_hash` must be unique/indexed. `AztekSession.user_id` must be unique. `AuditLog.user_id` is nullable so failed login of an unknown username can be recorded without inventing a user. All timestamps are timezone-aware UTC.

`Database` must set `check_same_thread=False` only for SQLite and expose a context manager that commits on success and rolls back on exception.

- [ ] **Step 4: Add Alembic migration and test fixture**

Configure Alembic target metadata as `Base.metadata`. Generate and inspect the initial migration:

Run: `alembic revision --autogenerate -m "auth and per-user sessions"`

Expected migration: creates exactly the eight tables above, foreign keys and unique indexes; downgrade drops them in reverse dependency order.

`tests/conftest.py` must create one temporary SQLite database per test, run `Base.metadata.create_all`, and close/dispose it after the test.

- [ ] **Step 5: Verify SQLite schema and migration**

Run: `python -B -m pytest tests/test_web_security.py -q`

Run: `alembic upgrade head`

Expected: tests PASS and local schema upgrades without errors.

- [ ] **Step 6: Commit**

```powershell
git add web/db.py web/models.py alembic.ini alembic tests/conftest.py tests/test_web_security.py
git commit -m "feat(web): add auth and job database schema"
```

---

### Task 3: Security primitives and web-session service

**Files:**
- Create: `web/security.py`
- Create: `web/auth_service.py`
- Test: `tests/test_web_security.py`

**Interfaces:**
- Produces: `hash_password(str) -> str`, `verify_password(str, str) -> bool`, `hash_token(str, Settings) -> str`, `encrypt_storage_state(dict, Settings) -> str`, `decrypt_storage_state(str, Settings) -> dict`
- Produces: `AuthService.create_user`, `authenticate`, `create_session`, `resolve_session`, `revoke_session`, `revoke_all_sessions`, `bootstrap_admin`

- [ ] **Step 1: Write failing primitive tests**

```python
def test_password_and_encryption_never_store_plaintext(settings):
    encoded = hash_password('correct horse')
    assert 'correct horse' not in encoded
    assert verify_password('correct horse', encoded)
    assert not verify_password('wrong', encoded)
    state = {'cookies': [{'name': 'token', 'value': 'secret'}], 'origins': []}
    ciphertext = encrypt_storage_state(state, settings)
    assert 'secret' not in ciphertext
    assert decrypt_storage_state(ciphertext, settings) == state

def test_session_token_is_stored_as_hash(auth_service, db_session, member):
    raw = auth_service.create_session(db_session, member)
    record = db_session.scalar(select(WebSession).where(WebSession.user_id == member.id))
    assert raw != record.token_hash
    assert auth_service.resolve_session(db_session, raw).id == member.id
```

- [ ] **Step 2: Run and verify failure**

Run: `python -B -m pytest tests/test_web_security.py -q`

Expected: FAIL on missing security/auth functions.

- [ ] **Step 3: Implement primitives**

- Argon2 `PasswordHasher` verifies passwords and catches mismatch exceptions.
- Token generation uses `secrets.token_urlsafe(32)`.
- Token storage uses HMAC-SHA256 keyed by `APP_SECRET_KEY`.
- AES-GCM uses a 32-byte URL-safe-base64 `AZTEK_SESSION_ENCRYPTION_KEY`; serialize JSON with sorted keys, prepend a random 12-byte nonce, and return URL-safe base64.
- Decryption rejects malformed ciphertext with a domain-specific `InvalidEncryptedState` exception.

- [ ] **Step 4: Implement AuthService and bootstrap**

Implement `AuthService` with these exact public method contracts:

- `create_user(db: Session, username: str, password: str, role: str = 'member') -> User`
- `authenticate(db: Session, username: str, password: str) -> User | None`
- `create_session(db: Session, user: User) -> str`
- `resolve_session(db: Session, raw_token: str) -> User | None`
- `revoke_session(db: Session, raw_token: str) -> None`
- `revoke_all_sessions(db: Session, user_id: str) -> None`
- `bootstrap_admin(db: Session) -> User | None`

Normalize usernames with `strip().casefold()`, allow only 3–80 characters from `[a-z0-9._-]`, require password length at least 10, and allow roles only `admin/member`. Disabled users and expired/revoked sessions resolve to `None`.

- [ ] **Step 5: Run tests and commit**

Run: `python -B -m pytest tests/test_web_security.py -q`

Expected: PASS.

```powershell
git add web/security.py web/auth_service.py tests/test_web_security.py
git commit -m "feat(web): add password and session security"
```

---

### Task 4: Login/logout/account APIs and login UI

**Files:**
- Modify: `web/app.py`
- Create: `web/static/login.html`
- Create: `web/static/account.html`
- Test: `tests/test_web_auth.py`
- Modify: `tests/conftest.py`

**Interfaces:**
- Produces endpoints: `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`, `POST /api/auth/change-password`, `GET /login`, `GET /account`
- Produces app factory: `create_app(settings: Settings | None = None, database: Database | None = None) -> FastAPI`

- [ ] **Step 1: Write failing auth API tests**

```python
def test_login_sets_httponly_cookie_and_me_returns_user(client, member_password):
    response = client.post('/api/auth/login', json={
        'username': 'member', 'password': member_password})
    assert response.status_code == 200
    assert 'HttpOnly' in response.headers['set-cookie']
    assert response.json()['user']['username'] == 'member'
    assert client.get('/api/auth/me').json()['username'] == 'member'

def test_disabled_user_cannot_login(client, disabled_user):
    response = client.post('/api/auth/login', json={
        'username': disabled_user.username, 'password': 'valid-password'})
    assert response.status_code == 401
    assert 'username' not in response.json()['detail'].lower()
```

- [ ] **Step 2: Verify failure**

Run: `python -B -m pytest tests/test_web_auth.py -q`

Expected: FAIL with 404 endpoints.

- [ ] **Step 3: Refactor app construction and add auth dependencies**

`create_app` stores `settings`, `database`, `auth_service`, and a login throttle in `app.state`. Add:

```python
def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    raw = request.cookies.get('afc_session', '')
    user = request.app.state.auth_service.resolve_session(db, raw)
    if not user:
        raise HTTPException(status_code=401, detail='กรุณาเข้าสู่ระบบ')
    return user

def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != 'admin':
        raise HTTPException(status_code=403, detail='ไม่มีสิทธิ์ใช้งานส่วนนี้')
    return user
```

Rate limit login by IP to 5 failures in 10 minutes. Successful login clears that IP bucket. Login failure always returns the same Thai message. Set cookie with `httponly=True`, `secure=settings.session_cookie_secure`, `samesite='lax'`, `max_age=settings.session_ttl_seconds`.

- [ ] **Step 4: Build login/account pages**

`login.html` posts JSON to `/api/auth/login`, displays server error with `textContent`, and redirects to `/` on success. `account.html` reads `/api/auth/me`, supports password change, logout, and has a placeholder card whose only state at this task is “ระบบเชื่อม Aztek จะเปิดในขั้นถัดไป”. Do not interpolate untrusted HTML.

`GET /` redirects unauthenticated browsers to `/login`; API routes return JSON 401 rather than redirecting.

- [ ] **Step 5: Verify auth behavior**

Run: `python -B -m pytest tests/test_web_auth.py tests/test_web_api.py -q`

Expected: auth tests and existing API tests PASS; Item Finder APIs remain behavior-compatible until ownership guards are added in Task 6.

- [ ] **Step 6: Commit**

```powershell
git add web/app.py web/static/login.html web/static/account.html tests/conftest.py tests/test_web_auth.py
git commit -m "feat(web): require team account login"
```

---

### Task 5: Persistent owner-scoped workspace repository

**Files:**
- Create: `web/workspaces.py`
- Test: `tests/test_web_ownership.py`

**Interfaces:**
- Consumes: `WorkspaceRecord`, `PendingImportRecord`, `item_service.merge_imported`
- Produces: `WorkspaceRepository.create/get_owned/delete_owned/replace_template/add_pending/apply_pending/save_results`

- [ ] **Step 1: Write failing repository ownership tests**

```python
def test_workspace_repository_scopes_every_lookup(db_session, member, other_member):
    repo = WorkspaceRepository(db_session)
    workspace = repo.create(member.id, 'event', 'a.xlsx', [{'kind': '1'}])
    assert repo.get_owned(member.id, workspace.id).id == workspace.id
    with pytest.raises(WorkspaceNotFound):
        repo.get_owned(other_member.id, workspace.id)

def test_pending_import_cannot_cross_users(db_session, member, other_member):
    repo = WorkspaceRepository(db_session)
    workspace = repo.create(member.id, 'shop')
    pending = repo.add_pending(member.id, workspace.id, [('One', [{'kind': '1'}])], [])
    with pytest.raises(PendingImportNotFound):
        repo.apply_pending(other_member.id, pending.id, ['One'])
```

- [ ] **Step 2: Verify failure**

Run: `python -B -m pytest tests/test_web_ownership.py -q`

Expected: FAIL because repository does not exist.

- [ ] **Step 3: Implement owner-scoped repository**

Implement `WorkspaceRepository` with these exact public method contracts:

- `create(owner_user_id: str, mode: str, filename: str = '', criteria: list[dict] | None = None) -> WorkspaceRecord`
- `get_owned(owner_user_id: str, workspace_id: str) -> WorkspaceRecord`
- `delete_owned(owner_user_id: str, workspace_id: str) -> None`
- `replace_template(owner_user_id: str, workspace_id: str, filename: str, criteria: list[dict]) -> WorkspaceRecord`
- `add_pending(owner_user_id: str, workspace_id: str, sheets: list, skipped: list) -> PendingImportRecord`
- `apply_pending(owner_user_id: str, pending_id: str, selected_sheets: list[str]) -> WorkspaceRecord`
- `save_results(owner_user_id: str, workspace_id: str, *, game: str, results: list, not_found: list) -> WorkspaceRecord`

All `SELECT`, `UPDATE`, and `DELETE` paths include `owner_user_id`. Unknown and foreign IDs raise the same not-found exception. `apply_pending` performs load/merge/delete in one transaction and locks the workspace row on PostgreSQL with `with_for_update()`.

- [ ] **Step 4: Verify repository and concurrency behavior**

Run: `python -B -m pytest tests/test_web_ownership.py -q`

Expected: PASS, including two pending imports applied without lost updates.

- [ ] **Step 5: Commit**

```powershell
git add web/workspaces.py tests/test_web_ownership.py
git commit -m "feat(web): persist user-owned workspaces"
```

---

### Task 6: Protect Item Finder HTTP API and WebSocket ownership

**Files:**
- Modify: `web/app.py`
- Modify: `tests/test_web_api.py`
- Test: `tests/test_web_ownership.py`

**Interfaces:**
- Consumes: `require_user`, `WorkspaceRepository`
- Produces: authenticated owner-scoped versions of all current Item Finder endpoints

- [ ] **Step 1: Write failing cross-user API tests**

```python
def test_other_user_cannot_read_export_delete_or_bundle(client_for, member, other_member,
                                                        workspace_for_member):
    outsider = client_for(other_member)
    wid = workspace_for_member.id
    assert outsider.get(f'/api/workspaces/{wid}').status_code == 404
    assert outsider.get(f'/api/workspaces/{wid}/export.csv').status_code == 404
    assert outsider.delete(f'/api/workspaces/{wid}').status_code == 404
    assert outsider.post(f'/api/workspaces/{wid}/bundles',
                           json={'selected_indexes': []}).status_code == 404

def test_unauthenticated_websocket_is_rejected(anonymous_client):
    with pytest.raises(WebSocketDisconnect) as error:
        with anonymous_client.websocket_connect('/ws/search'):
            pass
    assert error.value.code == 4401
```

- [ ] **Step 2: Verify the tests expose current vulnerability**

Run: `python -B -m pytest tests/test_web_ownership.py -q`

Expected: FAIL because endpoints currently trust workspace ID and WebSocket accepts anonymous clients.

- [ ] **Step 3: Replace global `WORKSPACES` calls with per-request repository**

Every current API endpoint receives `user: User = Depends(require_user)` and `db: Session = Depends(get_db)`. Construct `WorkspaceRepository(db)` and pass `user.id` to every method. `GET /api/health` remains public; `/api/games`, `/api/modes`, `/api/template`, imports, workspaces, exports and bundles require login.

For WebSocket, resolve `afc_session` before `accept()`:

```python
raw = ws.cookies.get('afc_session', '')
with database.session() as db:
    user = auth_service.resolve_session(db, raw)
if not user:
    await ws.close(code=4401)
    return
await ws.accept()
```

Load the workspace with `get_owned(user.id, workspace_id)` and close with `4404` for an unknown/foreign workspace.

- [ ] **Step 4: Adapt existing API tests to authenticated fixtures**

Replace module-global anonymous `TestClient` use with `client` fixture logged in as `member`. Create workspaces through `WorkspaceRepository` using that member ID. Preserve every existing assertion for import, mode policy, result regrouping, export, bundle ordering and stale-result clearing.

- [ ] **Step 5: Run API regression tests**

Run: `python -B -m pytest tests/test_web_api.py tests/test_web_ownership.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add web/app.py tests/test_web_api.py tests/test_web_ownership.py tests/conftest.py
git commit -m "feat(web): enforce Item Finder resource ownership"
```

---

### Task 7: Audit service and admin user management

**Files:**
- Create: `web/audit.py`
- Modify: `web/app.py`
- Create: `web/static/admin.html`
- Test: `tests/test_web_admin_audit.py`

**Interfaces:**
- Produces: `write_audit(db, *, user_id, action, status, summary='', tool='', resource_type='', resource_id='', request=None)`
- Produces endpoints: `GET/POST /api/admin/users`, `PATCH /api/admin/users/{id}`, `POST /api/admin/users/{id}/reset-password`, `GET /api/admin/audit`

- [ ] **Step 1: Write failing authorization and redaction tests**

```python
def test_member_cannot_manage_users(member_client):
    assert member_client.get('/api/admin/users').status_code == 403

def test_admin_can_create_disable_and_reset_user(admin_client):
    created = admin_client.post('/api/admin/users', json={
        'username': 'new.member', 'password': 'temporary-pass', 'role': 'member'})
    assert created.status_code == 201
    uid = created.json()['id']
    assert admin_client.patch(f'/api/admin/users/{uid}',
                              json={'is_active': False}).status_code == 200
    assert admin_client.post(f'/api/admin/users/{uid}/reset-password',
                             json={'password': 'replacement-pass'}).status_code == 200

def test_audit_summary_removes_secrets(db_session, member):
    row = write_audit(db_session, user_id=member.id, action='test', status='ok',
                      summary={'password': 'bad', 'cookie': 'secret', 'count': 2})
    assert 'bad' not in row.summary and 'secret' not in row.summary
    assert 'count' in row.summary
```

- [ ] **Step 2: Verify failure**

Run: `python -B -m pytest tests/test_web_admin_audit.py -q`

Expected: FAIL on missing endpoints/service.

- [ ] **Step 3: Implement audit sanitizer and required actions**

Allow only scalar summary keys from an explicit allowlist (`count`, `mode`, `game`, `filename`, `format`, `reason`, `target_username`, `role`). Reject keys containing `password`, `token`, `cookie`, `authorization`, `storage`, or `secret`. Truncate serialized summary to 2,000 characters.

Instrument login success/failure/logout; user create/enable/disable/password reset; workspace create/delete; template/plan import; export; and bundle preview. Failed login may have null `user_id` and only a sanitized username fingerprint, never the entered password.

- [ ] **Step 4: Implement admin APIs and UI**

All admin endpoints use `require_admin`. Prevent an admin from disabling the final active admin. Resetting a password revokes all target sessions. `admin.html` uses `textContent`, lists users, provides create/disable/reset controls, and filters audit by `user_id`, `action`, `status`, `from`, and `to`.

- [ ] **Step 5: Run tests and commit**

Run: `python -B -m pytest tests/test_web_admin_audit.py tests/test_web_auth.py -q`

Expected: PASS.

```powershell
git add web/audit.py web/app.py web/static/admin.html tests/test_web_admin_audit.py tests/test_web_auth.py
git commit -m "feat(web): add admin accounts and audit log"
```

---

### Task 8: One-time pairing and encrypted Aztek session API

**Files:**
- Create: `web/aztek_sessions.py`
- Modify: `web/app.py`
- Test: `tests/test_aztek_pairing.py`

**Interfaces:**
- Produces: `AztekSessionService.create_pairing_token`, `consume_pairing_token`, `get_status`, `disconnect`, `load_storage_state`, `mark_expired`
- Produces endpoints: `POST /api/aztek/pairing-token`, `POST /api/aztek/pair`, `GET /api/aztek/status`, `DELETE /api/aztek/session`

- [ ] **Step 1: Write failing pairing tests**

```python
def test_pairing_token_is_one_time_and_state_is_encrypted(client, db_session, member):
    token = client.post('/api/aztek/pairing-token').json()['token']
    payload = valid_storage_state_payload(token)
    assert client.post('/api/aztek/pair', json=payload).status_code == 200
    assert client.post('/api/aztek/pair', json=payload).status_code == 410
    record = db_session.scalar(select(AztekSession).where(AztekSession.user_id == member.id))
    assert payload['storage_state']['cookies'][0]['value'] not in record.storage_state_encrypted

def test_pairing_rejects_foreign_cookie_domain(client):
    token = client.post('/api/aztek/pairing-token').json()['token']
    payload = valid_storage_state_payload(token)
    payload['storage_state']['cookies'][0]['domain'] = '.example.com'
    assert client.post('/api/aztek/pair', json=payload).status_code == 422
```

- [ ] **Step 2: Verify failure**

Run: `python -B -m pytest tests/test_aztek_pairing.py -q`

Expected: FAIL with missing endpoints/service.

- [ ] **Step 3: Implement validation and service**

Accepted storage state shape:

```python
class StorageStatePayload(BaseModel):
    pairing_token: str = Field(min_length=20, max_length=200)
    account_label: str = Field(default='', max_length=120)
    storage_state: dict
```

Require `cookies` and `origins` lists. Every cookie domain must equal or be a parent-dot form of `aztek-tools.combo-interactive.com`; every origin must equal `settings.aztek_origin`. Limit request body to 256 KiB, cookie count to 200, localStorage entries to 500, and individual names/values to bounded lengths. Return 404 for unknown token and 410 for expired/used token without revealing owner.

Creating a token invalidates unused prior tokens for that user. Consuming it stores AES-GCM ciphertext in an upserted `AztekSession`, marks token used in the same transaction, and audits `aztek.connected`.

- [ ] **Step 4: Implement status/disconnect and audit**

`GET /api/aztek/status` returns only `status`, `account_label`, `updated_at`, `last_used_at`; never ciphertext. Disconnect deletes/revokes stored state and audits the action. Pairing endpoint is the only non-cookie-auth endpoint and is rate-limited by IP and token hash.

- [ ] **Step 5: Run tests and commit**

Run: `python -B -m pytest tests/test_aztek_pairing.py tests/test_web_security.py -q`

Expected: PASS.

```powershell
git add web/aztek_sessions.py web/app.py tests/test_aztek_pairing.py
git commit -m "feat(web): pair encrypted Aztek sessions"
```

---

### Task 9: Private Chrome Extension

**Files:**
- Create: `extension/manifest.json`
- Create: `extension/config.js`
- Create: `extension/popup.html`
- Create: `extension/popup.js`
- Create: `extension/content.js`
- Create: `docs/install-extension.md`
- Test: `tests/test_extension_contract.py`

**Interfaces:**
- Consumes: `POST /api/aztek/pair`
- Produces: storage-state payload compatible with `StorageStatePayload`

- [ ] **Step 1: Write failing static contract tests**

```python
def test_extension_permissions_are_scoped_to_aztek():
    manifest = json.loads(Path('extension/manifest.json').read_text('utf-8'))
    assert manifest['manifest_version'] == 3
    assert 'cookies' in manifest['permissions']
    assert manifest['host_permissions'] == [
        'https://aztek-tools.combo-interactive.com/*',
        'http://localhost:8000/*',
    ]

def test_extension_posts_pairing_payload_without_password():
    source = Path('extension/popup.js').read_text('utf-8')
    assert '/api/aztek/pair' in source
    assert 'storage_state' in source
    assert 'password' not in source.casefold()
```

- [ ] **Step 2: Verify failure**

Run: `python -B -m pytest tests/test_extension_contract.py -q`

Expected: FAIL because extension files do not exist.

- [ ] **Step 3: Implement Manifest V3 session collection**

`popup.js` must:

1. Require a non-empty pairing token.
2. Find an active tab whose URL origin is exactly Aztek.
3. Call `chrome.cookies.getAll({domain: 'aztek-tools.combo-interactive.com'})`.
4. Ask `content.js` for `Object.entries(localStorage)` on the active Aztek tab.
5. Convert cookies to Playwright fields (`name`, `value`, `domain`, `path`, `expires`, `httpOnly`, `secure`, `sameSite`).
6. POST `{pairing_token, account_label, storage_state:{cookies, origins:[{origin, localStorage}]}}` to `${BACKEND_ORIGIN}/api/aztek/pair`.
7. Clear the token input and display success/error using `textContent`.

`config.js` exports only `BACKEND_ORIGIN`; it contains no secret. Manifest reads cookies only from the exact Aztek host. Backend origin is added to `host_permissions` for the actual deployment before distribution; local package includes `http://localhost:8000/*`.

- [ ] **Step 4: Document private installation**

Document: open `chrome://extensions`, enable Developer mode, Load unpacked, select `extension/`, log into Aztek in a normal tab, copy pairing token from `/account`, open extension, paste and connect. Include how to change `BACKEND_ORIGIN` for Render and reload the extension.

- [ ] **Step 5: Run tests and commit**

Run: `python -B -m pytest tests/test_extension_contract.py -q`

Expected: PASS.

```powershell
git add extension docs/install-extension.md tests/test_extension_contract.py
git commit -m "feat(extension): import per-user Aztek sessions"
```

---

### Task 10: Per-user Playwright context, queue, jobs, and session expiry

**Files:**
- Modify: `web/search_runner.py`
- Create: `web/search_coordinator.py`
- Modify: `web/app.py`
- Modify: `tests/test_web_runner.py`
- Test: `tests/test_web_search_auth.py`

**Interfaces:**
- Consumes: `AztekSessionService.load_storage_state`, `WorkspaceRepository`, `Job`, `write_audit`
- Produces: `HeadlessFinder.run(data: dict, storage_state: dict) -> None`, `SearchCoordinator.run(user_id: str, workspace_id: str, request_data: dict, emit: Callable[[dict], Awaitable[None]]) -> None`, `AztekSessionExpired`

- [ ] **Step 1: Write failing runner isolation tests**

```python
@pytest.mark.asyncio
async def test_web_runner_uses_non_persistent_context(monkeypatch, storage_state):
    fake = FakePlaywright()
    monkeypatch.setattr(search_runner, 'async_playwright', lambda: fake)
    finder = make_finder()
    await finder.run(valid_search_data(), storage_state)
    assert fake.chromium.launch_calls == [{'headless': True}]
    assert fake.browser.new_context_calls == [{'storage_state': storage_state}]
    assert fake.chromium.persistent_calls == []

def test_search_requires_connected_aztek_session(authenticated_client, workspace):
    with authenticated_client.websocket_connect('/ws/search') as ws:
        ws.send_json(valid_search_request(workspace.id))
        assert ws.receive_json()['code'] == 'aztek_session_required'
```

- [ ] **Step 2: Verify failure**

Run: `python -B -m pytest tests/test_web_runner.py tests/test_web_search_auth.py -q`

Expected: FAIL because web runner still delegates to desktop `_auto` and persistent profile.

- [ ] **Step 3: Add non-persistent web runner**

Do not change `item_finder.App._auto`; desktop keeps its profile. Add to `HeadlessFinder`:

```python
async def run(self, data: dict, storage_state: dict) -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=storage_state)
        page = await context.new_page()
        try:
            await page.goto(data['url'], wait_until='domcontentloaded', timeout=30000)
            if await is_login_page(page):
                raise AztekSessionExpired('Aztek session หมดอายุ')
            await self._search_all(page, data)
        finally:
            await context.close()
            await browser.close()
```

`is_login_page` checks auth URL/path and absence of the authenticated app shell after SPA settles; it must not infer expiry merely from an empty result table.

- [ ] **Step 4: Implement coordinator and persisted job lifecycle**

`SearchCoordinator` owns `asyncio.Semaphore(settings.browser_concurrency)`. Before entering the gate create a `queued` Job; update to `running`, then `done/failed/cancelled`. Store sanitized log lines with a bounded maximum. On `AztekSessionExpired`, mark the user's session expired, job failed with reason, emit `{type:'error', code:'aztek_session_expired'}`, and audit `aztek.expired` plus `item_finder.failed`.

On success persist workspace results through `save_results`, set `last_used_at`, and audit `item_finder.completed`. Always release the semaphore and close browser resources.

- [ ] **Step 5: Wire WebSocket to coordinator**

After authenticated ownership checks, require `AztekSession.status == connected`. Emit a `job` message containing job ID and queue state. Disconnect sets `finder._cancel=True`; coordinator records `cancelled`. Never pass encrypted ciphertext to `HeadlessFinder`—decrypt inside the service immediately before calling it.

- [ ] **Step 6: Run runner/API tests and commit**

Run: `python -B -m pytest tests/test_web_runner.py tests/test_web_search_auth.py tests/test_web_api.py -q`

Expected: PASS; assertions confirm zero `launch_persistent_context` use in web execution.

```powershell
git add web/search_runner.py web/search_coordinator.py web/app.py tests/test_web_runner.py tests/test_web_search_auth.py tests/test_web_api.py
git commit -m "feat(web): run Item Finder with per-user Aztek sessions"
```

---

### Task 11: Auth-aware Item Finder, account connection, and admin UI integration

**Files:**
- Modify: `web/static/index.html`
- Modify: `web/static/account.html`
- Modify: `web/static/admin.html`
- Modify: `tests/test_web_ui.py`

**Interfaces:**
- Consumes: `/api/auth/me`, `/api/aztek/status`, `/api/aztek/pairing-token`, authenticated Item Finder APIs
- Produces: complete browser navigation and session-expiry recovery flow

- [ ] **Step 1: Write failing UI contract tests**

```python
def test_item_finder_header_has_identity_connection_and_logout():
    for fragment in ('currentUser', 'aztekStatus', 'btnAccount', 'btnLogout'):
        assert f'id="{fragment}"' in INDEX_HTML

def test_account_page_can_create_pairing_token_without_rendering_secrets_as_html():
    assert '/api/aztek/pairing-token' in ACCOUNT_HTML
    assert 'pairingToken' in ACCOUNT_HTML
    assert '.innerHTML' not in ACCOUNT_HTML
```

- [ ] **Step 2: Verify failure**

Run: `python -B -m pytest tests/test_web_ui.py -q`

Expected: FAIL on missing elements.

- [ ] **Step 3: Integrate user/session state into Item Finder**

At `init()`, fetch `/api/auth/me` and `/api/aztek/status` before enabling search. If auth returns 401, redirect to `/login`. Display username/role; show `เชื่อมแล้ว`, `ยังไม่ได้เชื่อม`, or `หมดอายุ`. Disable only the search action when session is invalid; imports and reviewing prior results remain usable.

Wrap `fetch` in `apiFetch`: on 401 redirect to login; otherwise return response. WebSocket handles close code 4401 and messages `aztek_session_required/expired` by disabling search and linking to `/account` without erasing already-persisted successful results.

- [ ] **Step 4: Complete account/admin navigation**

Account page creates a pairing token, displays countdown from 5:00, offers Copy, refreshes status every 5 seconds while pairing is pending, supports disconnect, password change and logout. Admin link appears only for role `admin`. All dynamic values use `textContent` or DOM properties.

- [ ] **Step 5: Run UI and API regressions**

Run: `python -B -m pytest tests/test_web_ui.py tests/test_web_auth.py tests/test_aztek_pairing.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add web/static/index.html web/static/account.html web/static/admin.html tests/test_web_ui.py
git commit -m "feat(web): add account and Aztek connection UI"
```

---

### Task 12: Deployment, end-to-end verification, and security audit

**Files:**
- Create: `Dockerfile`
- Create: `render.yaml`
- Create: `.env.example`
- Create: `docs/deploy-render.md`
- Modify: `README.md`
- Test: all test files

**Interfaces:**
- Produces: portable Render deployment using external PostgreSQL and documented bootstrap/admin/extension flow

- [ ] **Step 1: Add deploy configuration without secrets**

Docker image installs Python dependencies and Playwright Chromium, runs `alembic upgrade head`, then starts `uvicorn web.app:app --host 0.0.0.0 --port ${PORT}`. `render.yaml` declares one web service and environment-variable names only; it must not contain values for secrets or database credentials.

`.env.example` contains safe placeholders:

```dotenv
APP_ENV=production
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require
APP_SECRET_KEY=replace-with-long-random-value
AZTEK_SESSION_ENCRYPTION_KEY=replace-with-urlsafe-base64-32-byte-key
BOOTSTRAP_ADMIN_USERNAME=admin
BOOTSTRAP_ADMIN_PASSWORD=replace-with-strong-password
SESSION_COOKIE_SECURE=true
BROWSER_CONCURRENCY=1
```

- [ ] **Step 2: Document Render + Supabase/Neon setup**

Document database URL conversion to SQLAlchemy `postgresql+psycopg://`, Render env setup, first deploy migration, bootstrap admin login, changing bootstrap password, installing/configuring extension, reconnecting Aztek, and free-tier constraints. Include generation commands that print secrets locally but never write them into tracked files.

- [ ] **Step 3: Run secret and persistent-profile scans**

Run:

```powershell
git status --short
git ls-files | Select-String -Pattern 'dist|cabal_chrome_profile|\.env$|\.db$|\.sqlite'
rg -n "password\s*=|token\s*=|cookie\s*=|storage_state_encrypted\s*=" --glob '!docs/**' --glob '!tests/**'
```

Expected: runtime profile/database/env are not tracked; source scan contains declarations/placeholders only, no real values.

- [ ] **Step 4: Run full automated verification**

Run:

```powershell
python -m compileall -q web tests
python -B -m pytest -q -p no:cacheprovider
python tests/test_pure.py
```

Expected: all tests PASS; `test_pure.py` reports `ALL PASS (15)` or a higher count if intentionally expanded.

- [ ] **Step 5: Run local smoke flow**

Start with a temporary SQLite database and explicit dev secrets. Verify in browser:

1. `/` redirects to `/login`.
2. Bootstrap admin logs in.
3. Admin creates member.
4. Member logs in and creates pairing token.
5. Extension connects a test Aztek session.
6. Member imports a template and searches one item.
7. A second member receives 404 for the first member's workspace URL.
8. Admin audit shows login, pairing, import, search and export actions without secrets.

- [ ] **Step 6: Final commit**

```powershell
git add Dockerfile render.yaml .env.example docs/deploy-render.md README.md
git commit -m "docs(web): add secure Render deployment workflow"
```

---

## Self-review checklist

- Spec coverage: web auth, roles, admin provisioning, owner scope, pairing, encrypted storage, extension, per-user Playwright, queue, jobs, audit, SQLite/Postgres, Render and desktop fallback each map to at least one task.
- Secret safety: profile/database/env ignores happen in Task 1 before implementation commits; every later task stages explicit paths.
- Type consistency: `Settings`, `Database`, `AuthService`, `WorkspaceRepository`, `AztekSessionService`, `SearchCoordinator` signatures are introduced before consumers.
- Failure behavior: anonymous/foreign access, disabled users, expired/used pairing tokens, invalid cookie origins, expired Aztek session, worker crash and disconnect each have a specified test or lifecycle rule.
- Regression: original Item Finder APIs, UI, bundle ordering, Shop description, exports, desktop pure tests and source compilation are included in verification.
