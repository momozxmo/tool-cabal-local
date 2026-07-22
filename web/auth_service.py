from __future__ import annotations

import re
import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from web.models import User, WebSession, utc_now
from web.security import hash_password, hash_token, verify_password
from web.settings import Settings


_USERNAME_PATTERN = re.compile(r'[a-z0-9._-]{3,80}', re.ASCII)
_ALLOWED_ROLES = {'admin', 'member'}


def _normalize_username(username: str) -> str:
    if not isinstance(username, str):
        raise ValueError('username must be a string')
    normalized = username.strip().casefold()
    if _USERNAME_PATTERN.fullmatch(normalized) is None:
        raise ValueError(
            'username must be 3-80 characters from [a-z0-9._-]'
        )
    return normalized


class AuthService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def create_user(
        self,
        db: Session,
        username: str,
        password: str,
        role: str = 'member',
    ) -> User:
        normalized_username = _normalize_username(username)
        if not isinstance(password, str) or len(password) < 10:
            raise ValueError('password must contain at least 10 characters')
        if not isinstance(role, str) or role not in _ALLOWED_ROLES:
            raise ValueError('role must be admin or member')

        user = User(
            username=normalized_username,
            password_hash=hash_password(password),
            role=role,
        )
        db.add(user)
        db.flush()
        return user

    def authenticate(
        self, db: Session, username: str, password: str
    ) -> User | None:
        try:
            normalized_username = _normalize_username(username)
        except ValueError:
            return None
        if not isinstance(password, str):
            return None

        user = db.scalar(
            select(User).where(User.username == normalized_username)
        )
        if (
            user is None
            or not user.is_active
            or not verify_password(password, user.password_hash)
        ):
            return None

        user.last_login_at = utc_now()
        db.flush()
        return user

    def create_session(self, db: Session, user: User) -> str:
        if not user.is_active:
            raise ValueError('cannot create a session for a disabled user')

        raw_token = secrets.token_urlsafe(32)
        now = utc_now()
        db.add(WebSession(
            user_id=user.id,
            token_hash=hash_token(raw_token, self.settings),
            expires_at=now + timedelta(
                seconds=self.settings.session_ttl_seconds
            ),
        ))
        db.flush()
        return raw_token

    def resolve_session(self, db: Session, raw_token: str) -> User | None:
        if not isinstance(raw_token, str) or not raw_token:
            return None
        record = db.scalar(
            select(WebSession).where(
                WebSession.token_hash == hash_token(raw_token, self.settings)
            )
        )
        now = utc_now()
        if (
            record is None
            or record.revoked_at is not None
            or record.expires_at <= now
            or not record.user.is_active
        ):
            return None

        record.last_seen_at = now
        db.flush()
        return record.user

    def revoke_session(self, db: Session, raw_token: str) -> None:
        if not isinstance(raw_token, str) or not raw_token:
            return
        record = db.scalar(
            select(WebSession).where(
                WebSession.token_hash == hash_token(raw_token, self.settings)
            )
        )
        if record is not None and record.revoked_at is None:
            record.revoked_at = utc_now()
            db.flush()

    def revoke_all_sessions(self, db: Session, user_id: str) -> None:
        records = db.scalars(
            select(WebSession).where(
                WebSession.user_id == user_id,
                WebSession.revoked_at.is_(None),
            )
        ).all()
        if records:
            revoked_at = utc_now()
            for record in records:
                record.revoked_at = revoked_at
            db.flush()

    def bootstrap_admin(self, db: Session) -> User | None:
        if db.scalar(select(User.id).limit(1)) is not None:
            return None
        if not (
            self.settings.bootstrap_admin_username.strip()
            and self.settings.bootstrap_admin_password
        ):
            return None
        return self.create_user(
            db,
            self.settings.bootstrap_admin_username,
            self.settings.bootstrap_admin_password,
            role='admin',
        )
