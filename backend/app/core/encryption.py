"""
HIPAA-compliant AES-256-GCM field-level encryption for SQLAlchemy models.

Each encrypted value is stored as a base64-encoded blob:
    base64( nonce[12] + ciphertext + tag[16] )

The GCM tag is appended automatically by cryptography's AESGCM implementation
and is part of `ciphertext_with_tag` (last 16 bytes).
"""

import base64
import os
from typing import Any, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import String, types

from app.core.config import settings


# ---------------------------------------------------------------------------
# Low-level encrypt / decrypt
# ---------------------------------------------------------------------------

NONCE_BYTES = 12  # GCM recommended nonce length


def encrypt_field(plaintext: str, key: bytes) -> str:
    """
    Encrypt *plaintext* with AES-256-GCM using the given 32-byte *key*.

    Returns a base64-encoded string of  nonce + ciphertext+tag.
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(NONCE_BYTES)
    ciphertext_and_tag = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    blob = nonce + ciphertext_and_tag
    return base64.b64encode(blob).decode("ascii")


def decrypt_field(encrypted: str, key: bytes) -> str:
    """
    Decrypt a value produced by :func:`encrypt_field`.

    Raises ``ValueError`` on any decryption failure.
    """
    try:
        blob = base64.b64decode(encrypted)
        nonce = blob[:NONCE_BYTES]
        ciphertext_and_tag = blob[NONCE_BYTES:]
        aesgcm = AESGCM(key)
        plaintext_bytes = aesgcm.decrypt(nonce, ciphertext_and_tag, None)
        return plaintext_bytes.decode("utf-8")
    except Exception as exc:
        raise ValueError(f"Decryption failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Key derivation helper
# ---------------------------------------------------------------------------

def get_encryption_key() -> bytes:
    """
    Return the 32-byte encryption key from settings.

    The ENCRYPTION_KEY env var should be a 64-hex-character string (256 bits).
    If it's shorter / not hex, we derive 32 bytes via SHA-256 for robustness.
    """
    raw = settings.ENCRYPTION_KEY
    if not raw:
        raise RuntimeError("ENCRYPTION_KEY is not configured")
    try:
        key = bytes.fromhex(raw)
        if len(key) != 32:
            raise ValueError("Key must be exactly 32 bytes (64 hex chars)")
        return key
    except (ValueError, AttributeError):
        # Fall back: hash the raw string to get exactly 32 bytes
        import hashlib
        return hashlib.sha256(raw.encode("utf-8")).digest()


# ---------------------------------------------------------------------------
# SQLAlchemy TypeDecorator
# ---------------------------------------------------------------------------

class EncryptedString(types.TypeDecorator):
    """
    A SQLAlchemy column type that transparently encrypts/decrypts values.

    Usage::

        class MyModel(Base):
            secret = Column(EncryptedString)
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: Optional[str], dialect: Any) -> Optional[str]:
        """Encrypt before writing to DB."""
        if value is None:
            return None
        key = get_encryption_key()
        return encrypt_field(value, key)

    def process_result_value(self, value: Optional[str], dialect: Any) -> Optional[str]:
        """Decrypt after reading from DB."""
        if value is None:
            return None
        key = get_encryption_key()
        return decrypt_field(value, key)
