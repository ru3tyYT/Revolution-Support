#!/usr/bin/env python3
"""Standalone script to encrypt existing API keys.

This script can be run independently of Alembic migrations to encrypt
existing plaintext API keys in the database.

Usage:
    # First, set up your environment:
    export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    export DATABASE_URL="postgresql://user:password@host:port/database"

    # Then run the script:
    python scripts/migrate_encrypt_api_keys.py

    # Or with dry-run (to preview changes without applying):
    python scripts/migrate_encrypt_api_keys.py --dry-run

    # To check status only:
    python scripts/migrate_encrypt_api_keys.py --status

Features:
    - Encrypts all plaintext API keys
    - Skips already encrypted keys
    - Provides detailed logging
    - Supports dry-run mode
    - Handles errors gracefully
    - Can check encryption status
"""

import argparse
import logging
import os
import sys
from typing import List, Tuple

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
except ImportError:
    print("ERROR: SQLAlchemy is required. Install with: pip install sqlalchemy")
    sys.exit(1)

try:
    from bot.utils.encryption import EncryptionManager, ENCRYPTION_PREFIX, EncryptionKeyError
except ImportError:
    print("ERROR: Could not import encryption module.")
    print("Make sure the cryptography library is installed: pip install cryptography")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get database URL from environment or prompt user."""
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        logger.error("\nDATABASE_URL environment variable not set.")
        logger.error("Please set it to your PostgreSQL database URL.")
        logger.error("Example: postgresql://user:password@localhost:5432/supportbot")
        sys.exit(1)

    return db_url


def get_encryption_manager() -> EncryptionManager:
    """Initialize encryption manager from environment."""
    encryption_key = os.getenv("ENCRYPTION_KEY")

    if not encryption_key:
        logger.error("\n" + "=" * 70)
        logger.error("ERROR: ENCRYPTION_KEY environment variable not set!")
        logger.error("=" * 70)
        logger.error("\nTo generate an encryption key, run:")
        logger.error(
            '   export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")'
        )
        logger.error("\nOr use the encryption utility:")
        logger.error("   python bot/utils/encryption.py --generate-key")
        logger.error("=" * 70 + "\n")
        sys.exit(1)

    try:
        return EncryptionManager(encryption_key)
    except EncryptionKeyError as e:
        logger.error(f"\nERROR: Invalid encryption key: {e}")
        sys.exit(1)


def get_api_keys(session: Session) -> List[Tuple]:
    """Fetch all API keys from the database."""
    result = session.execute(
        text(
            "SELECT id, service_name, key_name, api_key FROM api_keys ORDER BY service_name, key_name"
        )
    )
    return result.fetchall()


def check_encryption_status(session: Session) -> dict:
    """Check the encryption status of all API keys."""
    keys = get_api_keys(session)

    total = len(keys)
    encrypted = sum(1 for k in keys if k[3] and k[3].startswith(ENCRYPTION_PREFIX))
    plaintext = total - encrypted

    return {"total": total, "encrypted": encrypted, "plaintext": plaintext, "keys": keys}


def encrypt_key(
    session: Session,
    key_id: str,
    service_name: str,
    key_name: str,
    api_key_value: str,
    manager: EncryptionManager,
    dry_run: bool = False,
) -> bool:
    """Encrypt a single API key.

    Args:
        session: Database session
        key_id: API key ID
        service_name: Service name
        key_name: Key name
        api_key_value: Current (plaintext) API key value
        manager: EncryptionManager instance
        dry_run: If True, don't actually update the database

    Returns:
        True if successful, False otherwise
    """
    # Skip if already encrypted or empty
    if not api_key_value:
        logger.info(f"  Skipping {service_name}/{key_name}: Empty value")
        return True

    if api_key_value.startswith(ENCRYPTION_PREFIX):
        logger.info(f"  Skipping {service_name}/{key_name}: Already encrypted")
        return True

    try:
        # Encrypt the key
        encrypted_value = manager.encrypt(api_key_value)

        if not dry_run:
            # Update the database
            session.execute(
                text("UPDATE api_keys SET api_key = :encrypted WHERE id = :id"),
                {"encrypted": encrypted_value, "id": key_id},
            )

        logger.info(f"  {'Would encrypt' if dry_run else 'Encrypted'}: {service_name}/{key_name}")
        return True

    except Exception as e:
        logger.error(f"  ERROR encrypting {service_name}/{key_name}: {e}")
        return False


def migrate_api_keys(dry_run: bool = False) -> dict:
    """Migrate all API keys to encrypted format.

    Args:
        dry_run: If True, don't actually update the database

    Returns:
        Dictionary with migration statistics
    """
    # Get configuration
    db_url = get_database_url()
    manager = get_encryption_manager()

    # Create database engine
    engine = create_engine(db_url)

    stats = {"total": 0, "encrypted": 0, "skipped": 0, "errors": 0}

    with Session(engine) as session:
        try:
            # Get all API keys
            keys = get_api_keys(session)
            stats["total"] = len(keys)

            logger.info(f"\nProcessing {len(keys)} API keys...")
            logger.info("=" * 70)

            for row in keys:
                key_id, service_name, key_name, api_key_value = row

                # Check current status
                if not api_key_value:
                    stats["skipped"] += 1
                    continue

                if api_key_value.startswith(ENCRYPTION_PREFIX):
                    stats["skipped"] += 1
                    continue

                # Encrypt the key
                success = encrypt_key(
                    session, key_id, service_name, key_name, api_key_value, manager, dry_run
                )

                if success:
                    stats["encrypted"] += 1
                else:
                    stats["errors"] += 1

            if dry_run:
                logger.info("\n" + "=" * 70)
                logger.info("DRY RUN MODE - No changes were made")
                session.rollback()
            else:
                session.commit()
                logger.info("\n" + "=" * 70)
                logger.info("Changes committed successfully")

        except Exception as e:
            session.rollback()
            logger.error(f"\nERROR during migration: {e}")
            raise

    return stats


def print_status():
    """Print the current encryption status."""
    db_url = get_database_url()
    engine = create_engine(db_url)

    with Session(engine) as session:
        status = check_encryption_status(session)

    logger.info("\n" + "=" * 70)
    logger.info("API Key Encryption Status")
    logger.info("=" * 70)
    logger.info(f"\nTotal API keys:     {status['total']}")
    logger.info(
        f"Encrypted:          {status['encrypted']} ({status['encrypted'] / status['total'] * 100:.1f}%)"
    )
    logger.info(
        f"Plaintext (legacy): {status['plaintext']} ({status['plaintext'] / status['total'] * 100:.1f}%)"
    )

    if status["plaintext"] > 0:
        logger.warning("\nWARNING: Some API keys are stored as plaintext (INSECURE)")
        logger.info("\nPlaintext keys:")
        for row in status["keys"]:
            if row[3] and not row[3].startswith(ENCRYPTION_PREFIX):
                logger.info(f"  - {row[1]}/{row[2]}")
        logger.info("\nRun this script without --status to encrypt them:")
        logger.info("   python scripts/migrate_encrypt_api_keys.py")
    else:
        logger.info("\nAll API keys are encrypted.")

    logger.info("=" * 70 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Encrypt API keys in the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Check status only:
    python scripts/migrate_encrypt_api_keys.py --status
    
    # Preview changes (dry-run):
    python scripts/migrate_encrypt_api_keys.py --dry-run
    
    # Actually encrypt keys:
    python scripts/migrate_encrypt_api_keys.py
    
    # With verbose logging:
    python scripts/migrate_encrypt_api_keys.py -v
        """,
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without applying them"
    )
    parser.add_argument(
        "--status", action="store_true", help="Show current encryption status and exit"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.status:
        print_status()
        return

    # Run migration
    logger.info("\n" + "=" * 70)
    if args.dry_run:
        logger.info("API Key Encryption Migration (DRY RUN)")
    else:
        logger.info("API Key Encryption Migration")
    logger.info("=" * 70 + "\n")

    try:
        stats = migrate_api_keys(dry_run=args.dry_run)

        logger.info("\n" + "=" * 70)
        logger.info("Migration Summary")
        logger.info("=" * 70)
        logger.info(f"  Total keys:  {stats['total']}")
        logger.info(f"  Encrypted:   {stats['encrypted']}")
        logger.info(f"  Skipped:     {stats['skipped']}")
        logger.info(f"  Errors:      {stats['errors']}")

        if args.dry_run:
            logger.info("\nNOTE: This was a dry run. No changes were made.")
            logger.info("Run without --dry-run to apply changes.")

        logger.info("=" * 70 + "\n")

        if stats["errors"] > 0:
            sys.exit(1)

    except Exception as e:
        logger.exception(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
