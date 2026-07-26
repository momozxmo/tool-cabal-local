import base64
import os
import secrets
import warnings
from dataclasses import dataclass


# Local development secrets live in a gitignored .env beside the project. Without
# one, APP_SECRET_KEY is regenerated on every start and every restart signs
# people out — including out of the bookmarklet's pairing page, which needs a web
# session to accept the captured cookies.
_ENV_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')


def read_env_file(path=None):
    """Read KEY=VALUE lines and return them. Missing or unreadable file -> {}.

    Deliberately not a dotenv library, and deliberately not a writer: putting
    these into ``os.environ`` would leak one caller's file into every later
    reader in the process. The values are a fallback layer under the real
    environment instead.

    The path is resolved at call time, not bound as a default, so a test can
    point it somewhere harmless.
    """
    try:
        with open(path or _ENV_FILE, encoding='utf-8') as stream:
            lines = stream.readlines()
    except OSError:
        return {}
    values = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        key = key.strip()
        if key:
            values[key] = value.strip().strip('"').strip("'")
    return values


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
    # Shared SSO login host used by all four game servers; its cookies/origins
    # are equally valid parts of a captured Aztek session.
    aztek_auth_origin: str = 'https://auth.combo-interactive.com'
    local_desktop_mode: bool = False
    local_runtime_dir: str = ''
    local_launcher_secret: str = ''

    @classmethod
    def from_env(cls) -> 'Settings':
        # The real environment wins; the local .env only fills what it leaves out.
        from_file = read_env_file()

        def env(name, default=''):
            value = os.environ.get(name)
            if value is None:
                value = from_file.get(name, default)
            return value

        app_env = env('APP_ENV', 'development').strip().lower()
        production = app_env == 'production'
        local_desktop_mode = (
            env('LOCAL_DESKTOP_MODE', 'false').strip().lower() == 'true')
        if local_desktop_mode and app_env != 'local-desktop':
            raise ValueError(
                'LOCAL_DESKTOP_MODE requires APP_ENV=local-desktop')
        if app_env == 'local-desktop' and not local_desktop_mode:
            raise ValueError(
                'APP_ENV=local-desktop requires LOCAL_DESKTOP_MODE=true')
        local_runtime_dir = env('LOCAL_RUNTIME_DIR').strip()
        local_launcher_secret = env('LOCAL_LAUNCHER_SECRET').strip()
        if local_desktop_mode:
            missing_local = [
                name for name, value in (
                    ('LOCAL_RUNTIME_DIR', local_runtime_dir),
                    ('LOCAL_LAUNCHER_SECRET', local_launcher_secret),
                ) if not value
            ]
            if missing_local:
                raise ValueError(
                    'missing local settings: ' + ', '.join(missing_local))
        app_secret = env('APP_SECRET_KEY').strip()
        encryption_key = env('AZTEK_SESSION_ENCRYPTION_KEY').strip()
        no_default_admin = production or local_desktop_mode
        admin_user = env(
            'BOOTSTRAP_ADMIN_USERNAME',
            '' if no_default_admin else 'admin',
        ).strip()
        admin_password = env(
            'BOOTSTRAP_ADMIN_PASSWORD',
            '' if no_default_admin else 'admin123456',
        )
        if production:
            missing = [name for name, value in (
                ('APP_SECRET_KEY', app_secret),
                ('AZTEK_SESSION_ENCRYPTION_KEY', encryption_key),
                ('BOOTSTRAP_ADMIN_USERNAME', admin_user),
                ('BOOTSTRAP_ADMIN_PASSWORD', admin_password),
            ) if not value]
            if missing:
                raise ValueError('missing production settings: ' + ', '.join(missing))
        elif not app_secret:
            # Only when there is nothing to sign with: a development run that
            # sets APP_SECRET_KEY keeps its sessions across restarts, and saying
            # otherwise trains the reader to ignore the warning.
            warnings.warn(
                'using process-local development secrets; sessions will not survive restart',
                RuntimeWarning,
                stacklevel=2,
            )
        try:
            browser_concurrency = max(1, int(env('BROWSER_CONCURRENCY', '1')))
        except ValueError as exc:
            raise ValueError('BROWSER_CONCURRENCY must be an integer') from exc
        return cls(
            app_env=app_env,
            database_url=env('DATABASE_URL', 'sqlite:///./all_for_cabal_web.db'),
            app_secret_key=app_secret or secrets.token_urlsafe(48),
            aztek_encryption_key=encryption_key or base64.urlsafe_b64encode(
                os.urandom(32)).decode('ascii'),
            bootstrap_admin_username=admin_user,
            bootstrap_admin_password=admin_password,
            session_cookie_secure=(
                True if production
                else env('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
            ),
            browser_concurrency=browser_concurrency,
            local_desktop_mode=local_desktop_mode,
            local_runtime_dir=local_runtime_dir,
            local_launcher_secret=local_launcher_secret,
        )
