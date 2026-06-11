"""AES-256-GCM encryption for OAuth refresh tokens at rest."""

import base64
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings


class CryptoError(Exception):
    """Raised when encryption or decryption fails."""


@dataclass(frozen=True)
class EncryptedPayload:
    ciphertext: bytes
    key_id: str = "v1"


def _derive_key(key_b64: str) -> bytes:
    try:
        key = base64.b64decode(key_b64)
    except Exception as exc:
        raise CryptoError("Invalid TOKEN_ENCRYPTION_KEY encoding") from exc
    if len(key) != 32:
        raise CryptoError("TOKEN_ENCRYPTION_KEY must decode to 32 bytes")
    return key


def encrypt(plaintext: str, key_id: str = "v1") -> EncryptedPayload:
    settings = get_settings()
    key = _derive_key(settings.token_encryption_key)
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), key_id.encode("utf-8"))
    return EncryptedPayload(ciphertext=nonce + ciphertext, key_id=key_id)


def decrypt(payload: bytes, key_id: str = "v1") -> str:
    settings = get_settings()
    key = _derive_key(settings.token_encryption_key)
    if len(payload) < 13:
        raise CryptoError("Ciphertext too short")
    nonce, ciphertext = payload[:12], payload[12:]
    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, key_id.encode("utf-8"))
    except Exception as exc:
        raise CryptoError("Decryption failed") from exc
    return plaintext.decode("utf-8")
