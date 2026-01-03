#!/usr/bin/env python3
"""
Migration script to convert timestamps from DATETIME strings to Unix epoch seconds (INTEGER).

This script:
1. Validates current schema version is 1
2. Creates automatic backup with timestamp
3. Executes atomic transaction migration
4. Updates schema version to 2

Usage:
    python3 migrate_to_epoch.py                    # Migrate default database
    python3 migrate_to_epoch.py --dry-run          # Show what would be done
    python3 migrate_to_epoch.py --db-path /path/to/db  # Migrate specific database
"""

import argparse
import logging
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Get current schema version from database."""
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(version) as version FROM schema_version")
    row = cursor.fetchone()
    return row[0] if row and row[0] else 0


def get_record_count(conn: sqlite3.Connection) -> int:
    """Get total number of weather measurements."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM weather_measurements")
    row = cursor.fetchone()
    return row[0] if row else 0


def create_backup(db_path: str) -> str:
    """Create timestamped backup of database."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"

    logger.info(f"Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)
    logger.info(f"Backup created successfully")

    return backup_path


def migrate_to_epoch(db_path: str, dry_run: bool = False) -> bool:
    """
    Migrate database from DATETIME strings to Unix epoch INTEGER timestamps.

    Args:
        db_path: Path to SQLite database
        dry_run: If True, only show what would be done

    Returns:
        True if successful, False otherwise
    """
    if not Path(db_path).exists():
        logger.error(f"Database file not found: {db_path}")
        return False

    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Check current schema version
        version = get_schema_version(conn)
        logger.info(f"Current schema version: {version}")

        if version != 1:
            logger.error(f"Expected schema version 1, found {version}")
            logger.error("Migration can only run on schema version 1")
            conn.close()
            return False

        # Get current record count
        record_count = get_record_count(conn)
        logger.info(f"Current record count: {record_count}")

        if dry_run:
            logger.info("DRY RUN - Would perform the following:")
            logger.info(f"  1. Create backup of {db_path}")
            logger.info(f"  2. Add temporary timestamp_epoch INTEGER column")
            logger.info(f"  3. Convert {record_count} datetime strings to Unix epoch seconds")
            logger.info(f"  4. Create new table with INTEGER timestamp column")
            logger.info(f"  5. Copy all data to new table")
            logger.info(f"  6. Drop old table and rename new table")
            logger.info(f"  7. Recreate 3 indexes")
            logger.info(f"  8. Update schema version to 2")
            conn.close()
            return True

        # Create backup before migration
        backup_path = create_backup(db_path)

        # Execute migration in transaction
        logger.info("Starting migration transaction...")
        cursor = conn.cursor()

        # Begin transaction explicitly
        cursor.execute("BEGIN TRANSACTION")

        try:
            # Step 1: Add temporary epoch column
            logger.info("Adding temporary timestamp_epoch column...")
            cursor.execute("""
                ALTER TABLE weather_measurements
                ADD COLUMN timestamp_epoch INTEGER
            """)

            # Step 2: Convert all timestamps to Unix epoch seconds
            logger.info(f"Converting {record_count} timestamps to Unix epoch seconds...")
            cursor.execute("""
                UPDATE weather_measurements
                SET timestamp_epoch = CAST(strftime('%s', timestamp) AS INTEGER)
            """)

            # Step 3: Verify no NULL values
            cursor.execute("""
                SELECT COUNT(*) as null_count
                FROM weather_measurements
                WHERE timestamp_epoch IS NULL
            """)
            null_count = cursor.fetchone()[0]
            if null_count > 0:
                raise Exception(f"Found {null_count} NULL epoch timestamps after conversion")
            logger.info("All timestamps converted successfully (no NULLs)")

            # Step 4: Create new table with INTEGER timestamp
            logger.info("Creating new table with INTEGER timestamp...")
            cursor.execute("""
                CREATE TABLE weather_measurements_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    -- Timestamp (Unix epoch seconds)
                    timestamp INTEGER NOT NULL,

                    -- Temperature (Fahrenheit)
                    temp_outdoor REAL,
                    temp_indoor REAL,
                    feels_like REAL,
                    dew_point REAL,

                    -- Humidity (%)
                    humidity_outdoor INTEGER,
                    humidity_indoor INTEGER,

                    -- Pressure (inHg)
                    pressure_relative REAL,
                    pressure_absolute REAL,

                    -- Wind
                    wind_speed REAL,
                    wind_gust REAL,
                    wind_direction INTEGER,
                    wind_gust_direction INTEGER,
                    max_daily_gust REAL,

                    -- Rain (inches)
                    hourly_rain REAL,
                    daily_rain REAL,
                    weekly_rain REAL,
                    monthly_rain REAL,
                    yearly_rain REAL,

                    -- Solar/UV
                    solar_radiation REAL,
                    uv_index INTEGER,

                    -- Device info
                    mac_address TEXT NOT NULL,

                    -- Metadata
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                    -- Constraints
                    UNIQUE(timestamp, mac_address)
                )
            """)

            # Step 5: Copy data using epoch timestamps
            logger.info("Copying data to new table...")
            cursor.execute("""
                INSERT INTO weather_measurements_new
                SELECT
                    id,
                    timestamp_epoch,
                    temp_outdoor, temp_indoor, feels_like, dew_point,
                    humidity_outdoor, humidity_indoor,
                    pressure_relative, pressure_absolute,
                    wind_speed, wind_gust, wind_direction, wind_gust_direction, max_daily_gust,
                    hourly_rain, daily_rain, weekly_rain, monthly_rain, yearly_rain,
                    solar_radiation, uv_index,
                    mac_address,
                    created_at
                FROM weather_measurements
                ORDER BY id
            """)

            # Verify record count matches
            cursor.execute("SELECT COUNT(*) FROM weather_measurements_new")
            new_count = cursor.fetchone()[0]
            if new_count != record_count:
                raise Exception(f"Record count mismatch: original={record_count}, new={new_count}")
            logger.info(f"Copied {new_count} records successfully")

            # Step 6: Swap tables
            logger.info("Dropping old table and renaming new table...")
            cursor.execute("DROP TABLE weather_measurements")
            cursor.execute("ALTER TABLE weather_measurements_new RENAME TO weather_measurements")

            # Step 7: Recreate indexes
            logger.info("Recreating indexes...")
            cursor.execute("""
                CREATE INDEX idx_timestamp
                ON weather_measurements(timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX idx_mac_address
                ON weather_measurements(mac_address)
            """)
            cursor.execute("""
                CREATE INDEX idx_mac_timestamp
                ON weather_measurements(mac_address, timestamp DESC)
            """)

            # Step 8: Update schema version
            logger.info("Updating schema version to 2...")
            cursor.execute("INSERT INTO schema_version (version) VALUES (2)")

            # Commit transaction
            conn.commit()
            logger.info("Migration completed successfully!")
            logger.info(f"Backup saved at: {backup_path}")

            return True

        except Exception as e:
            # Rollback on any error
            conn.rollback()
            logger.error(f"Migration failed, rolled back changes: {e}")
            logger.error(f"Database restored to original state")
            logger.info(f"Backup available at: {backup_path}")
            return False

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return False

    finally:
        if conn:
            conn.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate weather logger database from DATETIME to Unix epoch timestamps"
    )
    parser.add_argument(
        "--db-path",
        default="data/weather.db",
        help="Path to database file (default: data/weather.db)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("Weather Logger Database Migration: DATETIME → Unix Epoch")
    logger.info("=" * 70)
    logger.info(f"Database: {args.db_path}")
    logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE MIGRATION'}")
    logger.info("")

    success = migrate_to_epoch(args.db_path, args.dry_run)

    if success:
        logger.info("")
        logger.info("=" * 70)
        if args.dry_run:
            logger.info("DRY RUN completed successfully")
        else:
            logger.info("MIGRATION completed successfully")
        logger.info("=" * 70)
        sys.exit(0)
    else:
        logger.error("")
        logger.error("=" * 70)
        logger.error("MIGRATION FAILED")
        logger.error("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
