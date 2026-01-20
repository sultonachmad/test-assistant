"""Encryption utilities for securing sensitive configuration values."""
import base64
import hashlib
import logging
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# Prefix to identify encrypted values
ENCRYPTED_PREFIX = "ENC:"


def _get_encryption_key(secret: str) -> bytes:
    """Derive a Fernet key from a secret string."""
    # Use SHA256 to get a consistent 32-byte key, then base64 encode for Fernet
    key_bytes = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(key_bytes)


def encrypt_value(value: str, secret: str) -> str:
    """
    Encrypt a value using the provided secret.
    Returns the encrypted value with ENC: prefix.
    """
    if not value or not secret:
        raise ValueError("Value and secret are required")

    key = _get_encryption_key(secret)
    fernet = Fernet(key)
    encrypted = fernet.encrypt(value.encode())
    return f"{ENCRYPTED_PREFIX}{encrypted.decode()}"


def decrypt_value(value: str, secret: str) -> str:
    """
    Decrypt a value if it has the ENC: prefix.
    Returns the original value if not encrypted.
    """
    if not value:
        return value

    # If not encrypted, return as-is
    if not value.startswith(ENCRYPTED_PREFIX):
        return value

    if not secret:
        logger.warning("Cannot decrypt value: no secret provided")
        return value

    try:
        encrypted_data = value[len(ENCRYPTED_PREFIX):]
        key = _get_encryption_key(secret)
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted_data.encode())
        return decrypted.decode()
    except InvalidToken:
        logger.error("Failed to decrypt value: invalid token or wrong secret")
        raise ValueError("Failed to decrypt value: invalid encryption key")
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        raise


def is_encrypted(value: str) -> bool:
    """Check if a value is encrypted (has ENC: prefix)."""
    return value.startswith(ENCRYPTED_PREFIX) if value else False


# CLI helper to encrypt values
if __name__ == "__main__":
    import sys
    import os

    print("=" * 50)
    print("Password Encryption Utility")
    print("=" * 50)

    # Get secret from environment or prompt
    secret = os.getenv("NEXTAUTH_SECRET")
    if not secret:
        secret = input("Enter your NEXTAUTH_SECRET: ").strip()

    if not secret:
        print("Error: NEXTAUTH_SECRET is required")
        sys.exit(1)

    # Get value to encrypt
    value = input("Enter the password to encrypt: ").strip()
    if not value:
        print("Error: Password is required")
        sys.exit(1)

    encrypted = encrypt_value(value, secret)
    print("\n" + "=" * 50)
    print("Encrypted value (copy this to your .env file):")
    print("=" * 50)
    print(encrypted)
    print("\n")
