"""Encryption utilities for sensitive data.

This module provides Fernet symmetric encryption for API keys and other
sensitive data stored in the database. It supports:
- Automatic key generation
- Encryption/decryption of sensitive values
- Backward compatibility with legacy plaintext keys
- Proper error handling and logging
"""

import base64
import logging
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

# Marker prefix to identify encrypted values
ENCRYPTION_PREFIX = "ENC::"


class EncryptionError(Exception):
    """Raised when encryption/decryption operations fail."""

    pass


class EncryptionKeyError(EncryptionError):
    """Raised when there's an issue with the encryption key."""

    pass


def generate_encryption_key() -> str:
    """Generate a new Fernet encryption key.

    Returns:
        A URL-safe base64-encoded 32-byte key suitable for Fernet.
        This key should be stored securely (e.g., in environment variables).

    Example:
        >>> key = generate_encryption_key()
        >>> print(f"Store this key: {key}")
    """
    key = Fernet.generate_key()
    return key.decode("utf-8")


def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> tuple[str, bytes]:
    """Derive a Fernet key from a password using PBKDF2.

    This is useful if you want to use a human-readable password
    instead of a random key.

    Args:
        password: The password to derive the key from.
        salt: Optional salt bytes. If not provided, a random salt is generated.

    Returns:
        A tuple of (base64-encoded key, salt bytes).

    Example:
        >>> key, salt = derive_key_from_password("my_secret_password")
        >>> # Store both key and salt securely
    """
    if salt is None:
        salt = os.urandom(16)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key.decode("utf-8"), salt


class EncryptionManager:
    """Manager for encryption operations.

    This class provides methods for encrypting and decrypting sensitive data
    using Fernet symmetric encryption. It handles key management and provides
    backward compatibility with legacy plaintext data.

    Usage:
        >>> manager = EncryptionManager()
        >>> encrypted = manager.encrypt("my_secret_key")
        >>> decrypted = manager.decrypt(encrypted)
        >>> print(decrypted)  # "my_secret_key"
    """

    def __init__(self, key: Optional[str] = None):
        """Initialize the encryption manager.

        Args:
            key: The encryption key. If not provided, will use
                 ENCRYPTION_KEY environment variable.

        Raises:
            EncryptionKeyError: If no key is provided and ENCRYPTION_KEY
                               environment variable is not set.
        """
        if key is None:
            key = os.getenv("ENCRYPTION_KEY")

        if not key:
            raise EncryptionKeyError(
                "Encryption key not provided. Set ENCRYPTION_KEY environment variable "
                "or pass key to EncryptionManager. Generate a key with: "
                'python -c "from bot.utils.encryption import generate_encryption_key; '
                'print(generate_encryption_key())"'
            )

        try:
            self._fernet = Fernet(key.encode("utf-8"))
        except Exception as e:
            raise EncryptionKeyError(f"Invalid encryption key: {e}")

    def encrypt(self, value: str) -> str:
        """Encrypt a string value.

        Args:
            value: The plaintext value to encrypt.

        Returns:
            The encrypted value with ENCRYPTION_PREFIX prepended.

        Raises:
            EncryptionError: If encryption fails.

        Example:
            >>> manager = EncryptionManager()
            >>> encrypted = manager.encrypt("my_api_key")
            >>> print(encrypted.startswith("ENC::"))  # True
        """
        if not value:
            return value

        # Don't double-encrypt
        if value.startswith(ENCRYPTION_PREFIX):
            return value

        try:
            encrypted = self._fernet.encrypt(value.encode("utf-8"))
            return f"{ENCRYPTION_PREFIX}{encrypted.decode('utf-8')}"
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt value: {e}")

    def decrypt(self, value: str) -> str:
        """Decrypt an encrypted string value.

        This method automatically detects whether a value is encrypted
        (by checking for ENCRYPTION_PREFIX) and handles both encrypted
        and plaintext (legacy) values.

        Args:
            value: The value to decrypt. Can be encrypted (with ENCRYPTION_PREFIX)
                   or plaintext.

        Returns:
            The decrypted plaintext value, or the original value if it was
            not encrypted.

        Raises:
            EncryptionError: If decryption fails (e.g., wrong key).

        Example:
            >>> manager = EncryptionManager()
            >>> # Decrypt encrypted value
            >>> decrypted = manager.decrypt("ENC::gAAAAAB...")
            >>> # Handle legacy plaintext
            >>> legacy = manager.decrypt("plaintext_key")
        """
        if not value:
            return value

        # Check if value is encrypted
        if not value.startswith(ENCRYPTION_PREFIX):
            # Legacy plaintext value - return as-is
            logger.debug("Value is not encrypted, returning as-is")
            return value

        # Remove prefix and decrypt
        encrypted_value = value[len(ENCRYPTION_PREFIX) :]

        try:
            decrypted = self._fernet.decrypt(encrypted_value.encode("utf-8"))
            return decrypted.decode("utf-8")
        except InvalidToken:
            logger.error("Decryption failed: Invalid token (wrong encryption key?)")
            raise EncryptionError(
                "Failed to decrypt value: Invalid encryption key or corrupted data"
            )
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise EncryptionError(f"Failed to decrypt value: {e}")

    def is_encrypted(self, value: str) -> bool:
        """Check if a value is encrypted.

        Args:
            value: The value to check.

        Returns:
            True if the value is encrypted, False otherwise.
        """
        return bool(value and value.startswith(ENCRYPTION_PREFIX))

    def rotate_key(self, value: str, new_manager: "EncryptionManager") -> str:
        """Re-encrypt a value with a new encryption key.

        This is useful for key rotation operations.

        Args:
            value: The encrypted value to re-encrypt.
            new_manager: EncryptionManager instance with the new key.

        Returns:
            The value re-encrypted with the new key.

        Example:
            >>> old_manager = EncryptionManager(old_key)
            >>> new_manager = EncryptionManager(new_key)
            >>> rotated = old_manager.rotate_key(encrypted_value, new_manager)
        """
        if not value:
            return value

        # Decrypt with current key
        decrypted = self.decrypt(value)

        # Re-encrypt with new key
        return new_manager.encrypt(decrypted)


# Global encryption manager instance (lazy-loaded)
_encryption_manager: Optional[EncryptionManager] = None


def get_encryption_manager() -> EncryptionManager:
    """Get the global encryption manager instance.

    This function provides a singleton pattern for the encryption manager,
    creating it on first call using the ENCRYPTION_KEY environment variable.

    Returns:
        The global EncryptionManager instance.

    Raises:
        EncryptionKeyError: If ENCRYPTION_KEY environment variable is not set.

    Example:
        >>> manager = get_encryption_manager()
        >>> encrypted = manager.encrypt("secret")
    """
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager


def encrypt_value(value: str) -> str:
    """Encrypt a value using the global encryption manager.

    This is a convenience function for simple encryption operations.

    Args:
        value: The plaintext value to encrypt.

    Returns:
        The encrypted value.

    Example:
        >>> encrypted = encrypt_value("my_secret")
    """
    return get_encryption_manager().encrypt(value)


def decrypt_value(value: str) -> str:
    """Decrypt a value using the global encryption manager.

    This is a convenience function for simple decryption operations.

    Args:
        value: The value to decrypt (encrypted or plaintext).

    Returns:
        The decrypted plaintext value.

    Example:
        >>> decrypted = decrypt_value("ENC::gAAAAAB...")
    """
    return get_encryption_manager().decrypt(value)


def is_encrypted(value: str) -> bool:
    """Check if a value is encrypted using the global encryption manager.

    Args:
        value: The value to check.

    Returns:
        True if the value is encrypted, False otherwise.
    """
    return get_encryption_manager().is_encrypted(value)


if __name__ == "__main__":
    # CLI utility for generating encryption keys
    import argparse

    parser = argparse.ArgumentParser(description="Encryption utilities")
    parser.add_argument("--generate-key", action="store_true", help="Generate a new encryption key")
    parser.add_argument(
        "--derive-from-password",
        metavar="PASSWORD",
        help="Derive an encryption key from a password",
    )

    args = parser.parse_args()

    if args.generate_key:
        key = generate_encryption_key()
        print(f"\nGenerated encryption key:\n{key}\n")
        print("Add this to your .env file as:")
        print(f"ENCRYPTION_KEY={key}")
    elif args.derive_from_password:
        key, salt = derive_key_from_password(args.derive_from_password)
        print(f"\nDerived key: {key}")
        print(f"Salt (hex): {salt.hex()}")
        print("\nAdd these to your .env file as:")
        print(f"ENCRYPTION_KEY={key}")
        print(f"# Store this salt securely: {salt.hex()}")
    else:
        parser.print_help()
