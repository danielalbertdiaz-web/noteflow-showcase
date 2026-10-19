import os
import pytest

from app.core.encryption import decrypt_field, encrypt_field, get_encryption_key


class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        key = get_encryption_key()
        plaintext = "Patient John Doe, knee surgery follow-up"
        encrypted = encrypt_field(plaintext, key)
        assert encrypted != plaintext
        decrypted = decrypt_field(encrypted, key)
        assert decrypted == plaintext

    def test_encrypt_produces_different_ciphertexts(self):
        key = get_encryption_key()
        plaintext = "Same text encrypted twice"
        enc1 = encrypt_field(plaintext, key)
        enc2 = encrypt_field(plaintext, key)
        # AES-GCM with random nonce should produce different ciphertexts
        assert enc1 != enc2

    def test_decrypt_with_wrong_key_fails(self):
        key = get_encryption_key()
        wrong_key = os.urandom(32)
        plaintext = "Sensitive PHI data"
        encrypted = encrypt_field(plaintext, key)
        with pytest.raises(Exception):
            decrypt_field(encrypted, wrong_key)

    def test_encrypt_empty_string(self):
        key = get_encryption_key()
        encrypted = encrypt_field("", key)
        decrypted = decrypt_field(encrypted, key)
        assert decrypted == ""

    def test_encrypt_unicode(self):
        key = get_encryption_key()
        plaintext = "Patient reports pain level 8/10 — ROM 0°-120°"
        encrypted = encrypt_field(plaintext, key)
        decrypted = decrypt_field(encrypted, key)
        assert decrypted == plaintext
