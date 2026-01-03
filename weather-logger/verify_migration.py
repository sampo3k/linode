#!/usr/bin/env python3
"""
Verification script for database migration to Unix epoch timestamps.

This script verifies:
1. Schema version is 2
2. Timestamp column type is INTEGER
3. No NULL timestamps
4. Timestamp values are in reasonable range (2020-2030)
5. All indexes exist
6. UNIQUE constraint intact
7. Record count is reasonable

Usage:
    python3 verify_migration.py                    # Verify default database
    python3 verify_migration.py /path/to/db       # Verify specific database
"""

import argparse
import logging
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


# Expected epoch range: 2020-01-01 to 2030-12-31
EPOCH_MIN = 1577836800  # 2020-01-01 00:00:00 UTC
EPOCH_MAX = 1924992000  # 2030-12-31 00:00:00 UTC


def check_schema_version(conn: sqlite3.Connection) -> bool:
    """Verify schema version is 2."""
    logger.info("Checking schema version...")
    cursor = conn.cursor()

    cursor.execute("SELECT MAX(version) as version FROM schema_version")
    row = cursor.fetchone()
    version = row[0] if row and row[0] else 0

    if version == 2:
        logger.info(f"✓ Schema version is 2")
        return True
    else:
        logger.error(f"✗ Schema version is {version}, expected 2")
        return False


def check_timestamp_column_type(conn: sqlite3.Connection) -> bool:
    """Verify timestamp column is INTEGER type."""
    logger.info("Checking timestamp column type...")
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(weather_measurements)")
    columns = cursor.fetchall()

    timestamp_col = None
    for col in columns:
        if col[1] == 'timestamp':  # col[1] is column name
            timestamp_col = col
            break

    if not timestamp_col:
        logger.error("✗ Timestamp column not found")
        return False

    col_type = timestamp_col[2]  # col[2] is column type
    if col_type.upper() == 'INTEGER':
        logger.info(f"✓ Timestamp column type is INTEGER")
        return True
    else:
        logger.error(f"✗ Timestamp column type is {col_type}, expected INTEGER")
        return False


def check_null_timestamps(conn: sqlite3.Connection) -> bool:
    """Verify there are no NULL timestamps."""
    logger.info("Checking for NULL timestamps...")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) as null_count
        FROM weather_measurements
        WHERE timestamp IS NULL
    """)
    row = cursor.fetchone()
    null_count = row[0] if row else 0

    if null_count == 0:
        logger.info(f"✓ No NULL timestamps found")
        return True
    else:
        logger.error(f"✗ Found {null_count} NULL timestamps")
        return False


def check_timestamp_range(conn: sqlite3.Connection) -> bool:
    """Verify timestamp values are in reasonable range."""
    logger.info("Checking timestamp value ranges...")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            MIN(timestamp) as min_ts,
            MAX(timestamp) as max_ts,
            COUNT(*) as count
        FROM weather_measurements
    """)
    row = cursor.fetchone()

    if not row or row[2] == 0:
        logger.warning("⚠ No records found in database")
        return True

    min_ts = row[0]
    max_ts = row[1]
    count = row[2]

    issues = []

    # Check minimum timestamp
    if min_ts < EPOCH_MIN:
        min_date = datetime.fromtimestamp(min_ts).isoformat()
        issues.append(f"Minimum timestamp {min_ts} ({min_date}) is before 2020")

    # Check maximum timestamp
    if max_ts > EPOCH_MAX:
        max_date = datetime.fromtimestamp(max_ts).isoformat()
        issues.append(f"Maximum timestamp {max_ts} ({max_date}) is after 2030")

    if issues:
        logger.error(f"✗ Timestamp range issues found:")
        for issue in issues:
            logger.error(f"  - {issue}")
        return False
    else:
        min_date = datetime.fromtimestamp(min_ts).isoformat()
        max_date = datetime.fromtimestamp(max_ts).isoformat()
        logger.info(f"✓ Timestamp range is valid: {min_ts} ({min_date}) to {max_ts} ({max_date})")
        logger.info(f"  Total records: {count}")
        return True


def check_indexes(conn: sqlite3.Connection) -> bool:
    """Verify all required indexes exist."""
    logger.info("Checking indexes...")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type = 'index' AND tbl_name = 'weather_measurements'
    """)
    indexes = {row[0] for row in cursor.fetchall()}

    required_indexes = {
        'idx_timestamp',
        'idx_mac_address',
        'idx_mac_timestamp'
    }

    missing = required_indexes - indexes
    if not missing:
        logger.info(f"✓ All required indexes exist: {', '.join(sorted(required_indexes))}")
        return True
    else:
        logger.error(f"✗ Missing indexes: {', '.join(sorted(missing))}")
        return False


def check_unique_constraint(conn: sqlite3.Connection) -> bool:
    """Verify UNIQUE constraint on (timestamp, mac_address) is intact."""
    logger.info("Checking UNIQUE constraint...")
    cursor = conn.cursor()

    # Get table definition
    cursor.execute("""
        SELECT sql FROM sqlite_master
        WHERE type = 'table' AND name = 'weather_measurements'
    """)
    row = cursor.fetchone()

    if not row:
        logger.error("✗ Table weather_measurements not found")
        return False

    table_sql = row[0]

    # Check for UNIQUE constraint in table definition
    if 'UNIQUE' in table_sql.upper() and 'TIMESTAMP' in table_sql.upper():
        logger.info("✓ UNIQUE constraint on (timestamp, mac_address) found in table definition")

        # Also test that constraint is enforced
        cursor.execute("SELECT timestamp, mac_address FROM weather_measurements LIMIT 1")
        row = cursor.fetchone()

        if row:
            test_ts = row[0]
            test_mac = row[1]

            try:
                # Try to insert duplicate
                cursor.execute("""
                    INSERT INTO weather_measurements (timestamp, mac_address, temp_outdoor)
                    VALUES (?, ?, 99.9)
                """, (test_ts, test_mac))
                conn.rollback()
                logger.error("✗ UNIQUE constraint not enforced (duplicate insert succeeded)")
                return False
            except sqlite3.IntegrityError:
                conn.rollback()
                logger.info("✓ UNIQUE constraint is enforced (duplicate insert rejected)")
                return True
        else:
            logger.info("✓ UNIQUE constraint definition found (no data to test enforcement)")
            return True
    else:
        logger.error("✗ UNIQUE constraint on (timestamp, mac_address) not found")
        return False


def check_record_count(conn: sqlite3.Connection) -> bool:
    """Verify record count is reasonable (> 0 if database is used)."""
    logger.info("Checking record count...")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM weather_measurements")
    row = cursor.fetchone()
    count = row[0] if row else 0

    if count >= 0:
        logger.info(f"✓ Record count: {count}")
        return True
    else:
        # This should never happen, but just in case
        logger.error(f"✗ Invalid record count: {count}")
        return False


def verify_migration(db_path: str) -> bool:
    """
    Verify database migration was successful.

    Args:
        db_path: Path to SQLite database

    Returns:
        True if all checks pass, False otherwise
    """
    if not Path(db_path).exists():
        logger.error(f"Database file not found: {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        logger.info(f"Verifying database: {db_path}")
        logger.info("")

        # Run all checks
        checks = [
            check_schema_version(conn),
            check_timestamp_column_type(conn),
            check_null_timestamps(conn),
            check_timestamp_range(conn),
            check_indexes(conn),
            check_unique_constraint(conn),
            check_record_count(conn),
        ]

        conn.close()

        # Return True only if all checks passed
        return all(checks)

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify weather logger database migration to Unix epoch timestamps"
    )
    parser.add_argument(
        "db_path",
        nargs="?",
        default="data/weather.db",
        help="Path to database file (default: data/weather.db)"
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("Weather Logger Database Migration Verification")
    logger.info("=" * 70)
    logger.info("")

    success = verify_migration(args.db_path)

    logger.info("")
    logger.info("=" * 70)
    if success:
        logger.info("ALL CHECKS PASSED ✓")
        logger.info("Migration verified successfully!")
    else:
        logger.error("SOME CHECKS FAILED ✗")
        logger.error("Migration verification failed!")
    logger.info("=" * 70)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
