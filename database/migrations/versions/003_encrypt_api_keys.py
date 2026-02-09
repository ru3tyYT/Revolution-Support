"""Migration to encrypt existing API keys.

Revision ID: 003_encrypt_api_keys
Revises: 002_add_forum_tables
Create Date: 2026-02-09

This migration encrypts all existing plaintext API keys in the database.
It should be run after the encryption module is configured.
"""

from typing import Sequence, Union
import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

# revision identifiers, used by Alembic.
revision: str = "003_encrypt_api_keys"
down_revision: Union[str, None] = "002_add_forum_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Encrypt all existing API keys.

    This migration:
    1. Checks for the ENCRYPTION_KEY environment variable
    2. Loads all existing API keys from the database
    3. Encrypts any plaintext keys
    4. Updates the database with encrypted values

    Note: Keys that are already encrypted (start with 'ENC::') are skipped.
    """
    # Check for encryption key
    encryption_key = os.getenv("ENCRYPTION_KEY")
    if not encryption_key:
        print("\n" + "=" * 70)
        print("WARNING: ENCRYPTION_KEY environment variable not set!")
        print("=" * 70)
        print("\nAPI keys will remain as plaintext (INSECURE).")
        print("\nTo encrypt API keys:")
        print("1. Generate an encryption key:")
        print(
            '   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
        print("2. Set the ENCRYPTION_KEY environment variable")
        print("3. Re-run this migration: alembic upgrade 003_encrypt_api_keys")
        print("\nOr run the standalone migration script:")
        print("   python scripts/migrate_encrypt_api_keys.py")
        print("=" * 70 + "\n")
        return

    try:
        from bot.utils.encryption import EncryptionManager, ENCRYPTION_PREFIX
    except ImportError as e:
        print(f"\nERROR: Could not import encryption module: {e}")
        print("Make sure the cryptography library is installed:")
        print("   pip install cryptography")
        return

    # Initialize encryption manager
    try:
        manager = EncryptionManager(encryption_key)
    except Exception as e:
        print(f"\nERROR: Failed to initialize encryption manager: {e}")
        return

    # Get database session
    bind = op.get_bind()
    session = Session(bind=bind)

    try:
        # Query all API keys
        result = session.execute(
            sa.text("SELECT id, service_name, key_name, api_key FROM api_keys")
        )

        keys = result.fetchall()
        encrypted_count = 0
        skipped_count = 0
        error_count = 0

        print(f"\nProcessing {len(keys)} API keys...")

        for row in keys:
            key_id, service_name, key_name, api_key_value = row

            # Skip if already encrypted or empty
            if not api_key_value or api_key_value.startswith(ENCRYPTION_PREFIX):
                skipped_count += 1
                continue

            try:
                # Encrypt the key
                encrypted_value = manager.encrypt(api_key_value)

                # Update the database
                session.execute(
                    sa.text("UPDATE api_keys SET api_key = :encrypted WHERE id = :id"),
                    {"encrypted": encrypted_value, "id": key_id},
                )

                encrypted_count += 1
                print(f"  Encrypted: {service_name}/{key_name}")

            except Exception as e:
                error_count += 1
                print(f"  ERROR encrypting {service_name}/{key_name}: {e}")

        # Commit all changes
        session.commit()

        print("\n" + "=" * 70)
        print("API Key Encryption Migration Complete")
        print("=" * 70)
        print(f"  Encrypted:  {encrypted_count}")
        print(f"  Skipped:    {skipped_count}")
        print(f"  Errors:     {error_count}")
        print("=" * 70 + "\n")

    except Exception as e:
        session.rollback()
        print(f"\nERROR during migration: {e}")
        raise
    finally:
        session.close()


def downgrade() -> None:
    """Decrypt all API keys (reverse migration).

    WARNING: This will store API keys as plaintext, which is insecure.
    Only use this for rollback scenarios.
    """
    # Check for encryption key
    encryption_key = os.getenv("ENCRYPTION_KEY")
    if not encryption_key:
        print("\nWARNING: ENCRYPTION_KEY not set. Cannot decrypt keys.")
        return

    try:
        from bot.utils.encryption import EncryptionManager, ENCRYPTION_PREFIX
    except ImportError:
        print("\nERROR: Could not import encryption module.")
        return

    # Initialize encryption manager
    try:
        manager = EncryptionManager(encryption_key)
    except Exception as e:
        print(f"\nERROR: Failed to initialize encryption manager: {e}")
        return

    # Get database session
    bind = op.get_bind()
    session = Session(bind=bind)

    try:
        # Query all API keys
        result = session.execute(
            sa.text("SELECT id, service_name, key_name, api_key FROM api_keys")
        )

        keys = result.fetchall()
        decrypted_count = 0
        skipped_count = 0
        error_count = 0

        print(f"\nWARNING: Decrypting {len(keys)} API keys (INSECURE operation)...")

        for row in keys:
            key_id, service_name, key_name, api_key_value = row

            # Skip if not encrypted or empty
            if not api_key_value or not api_key_value.startswith(ENCRYPTION_PREFIX):
                skipped_count += 1
                continue

            try:
                # Decrypt the key
                decrypted_value = manager.decrypt(api_key_value)

                # Update the database with plaintext
                session.execute(
                    sa.text("UPDATE api_keys SET api_key = :decrypted WHERE id = :id"),
                    {"decrypted": decrypted_value, "id": key_id},
                )

                decrypted_count += 1
                print(f"  Decrypted: {service_name}/{key_name}")

            except Exception as e:
                error_count += 1
                print(f"  ERROR decrypting {service_name}/{key_name}: {e}")

        # Commit all changes
        session.commit()

        print("\n" + "=" * 70)
        print("API Key Decryption Complete (INSECURE)")
        print("=" * 70)
        print(f"  Decrypted:  {decrypted_count}")
        print(f"  Skipped:    {skipped_count}")
        print(f"  Errors:     {error_count}")
        print("\nWARNING: API keys are now stored as PLAINTEXT!")
        print("=" * 70 + "\n")

    except Exception as e:
        session.rollback()
        print(f"\nERROR during downgrade: {e}")
        raise
    finally:
        session.close()
