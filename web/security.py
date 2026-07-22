from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import re
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from web.settings import Settings


_PASSWORD_HASHER = PasswordHasher()
_NONCE_BYTES = 12
_MIN_AES_GCM_PAYLOAD_BYTES = _NONCE_BYTES + 16
_URLSAFE_BASE64_PATTERN = re.compile(r'[A-Za-z0-9_-]*={0,2}\Z', re.ASCII)


class InvalidEncryptedState(ValueError):
    """Raised when encrypted browser storage state cannot be authenticated."""


def hash_password(password: str) -> str:
    return _PASSWORD_HASHER.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return _PASSWORD_HASHER.verify(encoded, password)
    except (InvalidHashError, VerificationError):
        return False


def hash_token(raw_token: str, settings: Settings) -> str:
    return hmac.new(
        settings.app_secret_key.encode('utf-8'),
        raw_token.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()


def _decode_urlsafe_base64(value: str) -> bytes:
    if _URLSAFE_BASE64_PATTERN.fullmatch(value) is None:
        raise binascii.Error('value is not URL-safe base64')
    encoded = value.encode('ascii')
    encoded += b'=' * (-len(encoded) % 4)
    return base64.b64decode(encoded, altchars=b'-_', validate=True)


def _encryption_key(settings: Settings) -> bytes:
    try:
        key = _decode_urlsafe_base64(settings.aztek_encryption_key)
    except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
        raise ValueError(
            'AZTEK_SESSION_ENCRYPTION_KEY must be URL-safe base64'
        ) from exc
    if len(key) != 32:
        raise ValueError(
            'AZTEK_SESSION_ENCRYPTION_KEY must decode to a 32-byte key'
        )
    return key


def encrypt_storage_state(state: dict[str, Any], settings: Settings) -> str:
    plaintext = json.dumps(
        state,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(',', ':'),
    ).encode('utf-8')
    nonce = os.urandom(_NONCE_BYTES)
    encrypted = AESGCM(_encryption_key(settings)).encrypt(
        nonce, plaintext, None
    )
    return base64.urlsafe_b64encode(nonce + encrypted).decode('ascii')


def decrypt_storage_state(ciphertext: str, settings: Settings) -> dict[str, Any]:
    try:
        payload = _decode_urlsafe_base64(ciphertext)
        if len(payload) < _MIN_AES_GCM_PAYLOAD_BYTES:
            raise InvalidEncryptedState('encrypted storage state is malformed')
        plaintext = AESGCM(_encryption_key(settings)).decrypt(
            payload[:_NONCE_BYTES], payload[_NONCE_BYTES:], None
        )
        state = json.loads(plaintext.decode('utf-8'))
        if not isinstance(state, dict):
            raise InvalidEncryptedState(
                'encrypted storage state must contain a JSON object'
            )
        return state
    except InvalidEncryptedState:
        raise
    except (
        UnicodeEncodeError,
        UnicodeDecodeError,
        binascii.Error,
        InvalidTag,
        json.JSONDecodeError,
        TypeError,
    ) as exc:
        raise InvalidEncryptedState(
            'encrypted storage state is malformed or has been tampered with'
        ) from exc
