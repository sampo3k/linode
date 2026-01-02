#!/usr/bin/env python3
"""
Weather Logger - Database Backup Script

Backs up the SQLite database to S3-compatible storage (Backblaze B2 or AWS S3).
"""
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from weather_logger import Config, ConfigError
from weather_logger.utils import setup_logging


logger = logging.getLogger(__name__)


class BackupManager:
    """
    Manages database backups to S3-compatible storage.
    """

    def __init__(self, config: Config):
        """
        Initialize backup manager.

        Args:
            config: Configuration instance
        """
        self.config = config

        # Get backup configuration
        backup_config = config.get("backup", {})

        self.enabled = backup_config.get("enabled", True)
        self.bucket_name = backup_config.get("bucket_name")
        self.endpoint_url = backup_config.get("endpoint_url")
        self.access_key = backup_config.get("access_key_id")
        self.secret_key = backup_config.get("secret_access_key")
        self.retention_days = backup_config.get("retention_days", 30)
        self.daily_retention_days = backup_config.get("daily_retention_days", 45)
        self.monthly_retention = backup_config.get("monthly_retention", True)
        self.prefix = backup_config.get("prefix", "weather-backups/")

        # Database path
        self.db_path = config.get("database.path", "data/weather.db")

        # Validate configuration
        if self.enabled:
            if not all([self.bucket_name, self.access_key, self.secret_key]):
                raise ConfigError(
                    "Backup is enabled but missing required configuration: "
                    "bucket_name, access_key_id, secret_access_key"
                )

        # Initialize S3 client
        if self.enabled:
            # Treat empty endpoint_url as None (use default AWS S3 endpoints)
            endpoint = self.endpoint_url if self.endpoint_url else None

            self.s3_client = boto3.client(
                's3',
                endpoint_url=endpoint,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
            )
            logger.info(f"Backup manager initialized for bucket: {self.bucket_name}")
        else:
            self.s3_client = None
            logger.info("Backup manager initialized (backups disabled)")

    def create_backup(self) -> bool:
        """
        Create a backup of the database and upload to S3.

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.info("Backups are disabled, skipping")
            return False

        try:
            # Check if database exists
            db_file = Path(self.db_path)
            if not db_file.exists():
                logger.error(f"Database file not found: {self.db_path}")
                return False

            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"weather_{timestamp}.db"
            s3_key = f"{self.prefix}{backup_filename}"

            logger.info(f"Creating backup: {backup_filename}")
            logger.info(f"Database size: {db_file.stat().st_size / 1024:.1f} KB")

            # Upload to S3
            start_time = time.time()

            self.s3_client.upload_file(
                str(db_file),
                self.bucket_name,
                s3_key,
                ExtraArgs={'Metadata': {
                    'backup-date': datetime.now().isoformat(),
                    'source': 'weather-logger',
                }}
            )

            upload_time = time.time() - start_time
            logger.info(f"Backup uploaded successfully in {upload_time:.2f}s: s3://{self.bucket_name}/{s3_key}")

            # Clean up old backups
            self.cleanup_old_backups()

            return True

        except ClientError as e:
            logger.error(f"S3 error during backup: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error during backup: {e}")
            return False

    def cleanup_old_backups(self) -> int:
        """
        Delete backups using tiered retention policy:
        - Keep all daily backups for the last daily_retention_days (default 45)
        - Keep one backup per month for backups older than daily_retention_days (forever)

        Returns:
            Number of backups deleted
        """
        if not self.enabled:
            return 0

        try:
            logger.info(f"Cleaning up backups with tiered retention policy:")
            logger.info(f"  - Daily backups: last {self.daily_retention_days} days")
            logger.info(f"  - Monthly backups: one per month (forever)")

            # Calculate cutoff date for daily retention
            daily_cutoff_date = datetime.now() - timedelta(days=self.daily_retention_days)

            # List objects in the bucket with our prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=self.prefix
            )

            if 'Contents' not in response:
                logger.info("No backups found in bucket")
                return 0

            # Group backups by age category
            recent_backups = []  # Within daily retention period
            old_backups = []  # Older than daily retention period

            for obj in response['Contents']:
                last_modified = obj['LastModified'].replace(tzinfo=None)

                if last_modified >= daily_cutoff_date:
                    # Recent backup - keep all
                    recent_backups.append(obj)
                else:
                    # Old backup - apply monthly retention
                    old_backups.append(obj)

            # For old backups, keep only one per month (first backup of each month)
            # Group by year-month
            monthly_backups = {}
            for obj in old_backups:
                last_modified = obj['LastModified'].replace(tzinfo=None)
                year_month = (last_modified.year, last_modified.month)

                if year_month not in monthly_backups:
                    monthly_backups[year_month] = []
                monthly_backups[year_month].append(obj)

            # Keep the first backup of each month, delete the rest
            deleted_count = 0
            for year_month, backups in monthly_backups.items():
                # Sort by date
                backups.sort(key=lambda x: x['LastModified'])

                # Keep the first one, delete the rest
                for obj in backups[1:]:
                    logger.info(f"Deleting redundant monthly backup: {obj['Key']} (from {obj['LastModified']})")
                    self.s3_client.delete_object(
                        Bucket=self.bucket_name,
                        Key=obj['Key']
                    )
                    deleted_count += 1

                if backups:
                    logger.debug(f"Keeping monthly backup for {year_month[0]}-{year_month[1]:02d}: {backups[0]['Key']}")

            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} redundant backup(s)")
                logger.info(f"Kept {len(recent_backups)} recent daily backups")
                logger.info(f"Kept {len(monthly_backups)} monthly backups")
            else:
                logger.info("No redundant backups to delete")
                logger.info(f"Current: {len(recent_backups)} daily backups, {len(monthly_backups)} monthly backups")

            return deleted_count

        except ClientError as e:
            logger.error(f"S3 error during cleanup: {e}")
            return 0
        except Exception as e:
            logger.exception(f"Unexpected error during cleanup: {e}")
            return 0

    def list_backups(self) -> list:
        """
        List all backups in the bucket.

        Returns:
            List of backup objects with metadata
        """
        if not self.enabled:
            return []

        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=self.prefix
            )

            if 'Contents' not in response:
                return []

            backups = []
            for obj in response['Contents']:
                backups.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                })

            # Sort by last modified (newest first)
            backups.sort(key=lambda x: x['last_modified'], reverse=True)

            return backups

        except ClientError as e:
            logger.error(f"S3 error listing backups: {e}")
            return []
        except Exception as e:
            logger.exception(f"Unexpected error listing backups: {e}")
            return []

    def restore_backup(self, backup_key: str, restore_path: str = None) -> bool:
        """
        Restore a backup from S3.

        Args:
            backup_key: S3 key of the backup to restore
            restore_path: Path to restore to (default: database path)

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.error("Backups are disabled, cannot restore")
            return False

        if restore_path is None:
            restore_path = self.db_path

        try:
            logger.info(f"Restoring backup from: {backup_key}")
            logger.info(f"Restore destination: {restore_path}")

            # Download from S3
            self.s3_client.download_file(
                self.bucket_name,
                backup_key,
                restore_path
            )

            logger.info(f"Backup restored successfully to {restore_path}")
            return True

        except ClientError as e:
            logger.error(f"S3 error during restore: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error during restore: {e}")
            return False


def main():
    """Main entry point for backup script."""
    print("Weather Logger - Database Backup")
    print("=" * 60)

    # Load configuration
    try:
        config = Config.load_from_file("config.yaml")
    except ConfigError as e:
        print(f"Configuration error: {e}")
        return 1

    # Setup logging
    log_config = config.get_logging_config()
    setup_logging(
        log_file=log_config["file"],
        log_level=log_config.get("level", "INFO"),
        log_format=log_config["format"],
    )

    logger.info("=" * 60)
    logger.info("Weather Logger - Database Backup")
    logger.info("=" * 60)

    # Create backup manager
    try:
        backup_manager = BackupManager(config)
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        print(f"Configuration error: {e}")
        return 1
    except Exception as e:
        logger.exception(f"Failed to initialize backup manager: {e}")
        return 1

    # Check if backups are enabled
    if not backup_manager.enabled:
        print("Backups are disabled in configuration")
        logger.warning("Backups are disabled, exiting")
        return 0

    # Perform backup
    print(f"Backing up database to: {backup_manager.bucket_name}")
    success = backup_manager.create_backup()

    if success:
        print("✓ Backup completed successfully")

        # List current backups
        backups = backup_manager.list_backups()
        if backups:
            print(f"\nCurrent backups ({len(backups)}):")
            for backup in backups[:5]:  # Show latest 5
                size_mb = backup['size'] / (1024 * 1024)
                print(f"  - {backup['key']} ({size_mb:.2f} MB) - {backup['last_modified']}")
            if len(backups) > 5:
                print(f"  ... and {len(backups) - 5} more")

        return 0
    else:
        print("✗ Backup failed - check logs for details")
        return 1


if __name__ == "__main__":
    sys.exit(main())
