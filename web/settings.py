import base64
import os
import secrets
import warnings
from dataclasses import dataclass


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
        else:
            warnings.warn(
                'using process-local development secrets; sessions will not survive restart',
                RuntimeWarning,
                stacklevel=2,
            )
        try:
            browser_concurrency = max(
                1, int(os.getenv('BROWSER_CONCURRENCY', '1'))
            )
        except ValueError as exc:
            raise ValueError('BROWSER_CONCURRENCY must be an integer') from exc
        return cls(
            app_env=app_env,
            database_url=os.getenv('DATABASE_URL', 'sqlite:///./all_for_cabal_web.db'),
            app_secret_key=app_secret or secrets.token_urlsafe(48),
            aztek_encryption_key=encryption_key or base64.urlsafe_b64encode(
                os.urandom(32)).decode('ascii'),
            bootstrap_admin_username=admin_user,
            bootstrap_admin_password=admin_password,
            session_cookie_secure=(
                True if production else os.getenv(
                    'SESSION_COOKIE_SECURE', 'false'
                ).lower() == 'true'
            ),
            browser_concurrency=browser_concurrency,
        )
