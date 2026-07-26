from __future__ import annotations

import hashlib
import hmac
import ipaddress
import secrets
import threading
import time
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from web.auth_service import AuthService
from web.models import User
from web.security import hash_token
from web.settings import Settings


LOCAL_OWNER_USERNAME = 'local.owner'
LOCAL_LAUNCH_TOKEN_TTL_SECONDS = 60


def is_loopback(host: str | None) -> bool:
    if not host:
        return False
    if host.casefold() == 'localhost':
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class LocalAccessService:
    """Authenticate the installed launcher without exposing an app password."""

    def __init__(
        self,
        settings: Settings,
        auth_service: AuthService,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.settings = settings
        self.auth_service = auth_service
        self._clock = clock
        self._pending_tokens: dict[str, float] = {}
        self._lock = threading.Lock()

    def enabled_for(self, client_host: str | None) -> bool:
        return self.settings.local_desktop_mode and is_loopback(client_host)

    def issue(
        self,
        provided_secret: str | None,
        client_host: str | None,
    ) -> str:
        expected = self.settings.local_launcher_secret
        if (
            not self.enabled_for(client_host)
            or not isinstance(provided_secret, str)
            or not expected
            or not hmac.compare_digest(provided_secret, expected)
        ):
            raise LookupError('local launcher access is unavailable')

        raw_token = secrets.token_urlsafe(32)
        token_key = hash_token(raw_token, self.settings)
        expires_at = self._clock() + LOCAL_LAUNCH_TOKEN_TTL_SECONDS
        with self._lock:
            self._purge_expired_locked()
            self._pending_tokens[token_key] = expires_at
        return raw_token

    def consume(self, raw_token: str, client_host: str | None) -> bool:
        if not self.enabled_for(client_host) or not isinstance(raw_token, str):
            return False
        token_key = hash_token(raw_token, self.settings)
        with self._lock:
            self._purge_expired_locked()
            expires_at = self._pending_tokens.pop(token_key, None)
        return expires_at is not None and self._clock() < expires_at

    def ensure_owner(self, db: Session) -> User:
        owner = db.scalar(
            select(User).where(User.username == LOCAL_OWNER_USERNAME)
        )
        if owner is not None:
            if not owner.is_active:
                raise RuntimeError('local owner account is disabled')
            return owner

        if db.scalar(select(User.id).limit(1)) is not None:
            raise RuntimeError(
                'local runtime database contains an unexpected user account'
            )

        # The internal credential is never shown or accepted by an HTTP login
        # route. Deriving it keeps even that database-only value distinct from
        # the launcher secret.
        internal_password = hmac.new(
            self.settings.app_secret_key.encode('utf-8'),
            self.settings.local_launcher_secret.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
        return self.auth_service.create_user(
            db,
            LOCAL_OWNER_USERNAME,
            internal_password,
            role='admin',
        )

    def _purge_expired_locked(self) -> None:
        now = self._clock()
        expired = [
            token_key
            for token_key, expires_at in self._pending_tokens.items()
            if expires_at <= now
        ]
        for token_key in expired:
            self._pending_tokens.pop(token_key, None)
