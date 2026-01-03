"""
SQLite database operations for Weather Logger.
"""
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .models import WeatherMeasurement


logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Base exception for database errors."""
    pass


class WeatherDatabase:
    """
    SQLite database manager for weather measurements.

    Handles schema initialization, data insertion, and queries.
    """

    def __init__(self, db_path: str):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

        # Ensure database directory exists
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized database at {db_path}")

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        Yields:
            sqlite3.Connection instance

        Example:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM weather_measurements")
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            # Enable WAL mode for better concurrent access
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA foreign_keys=ON")

            # Use Row factory for dict-like access
            conn.row_factory = sqlite3.Row

            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                conn.rollback()
            raise DatabaseError(f"Database connection error: {e}")
        finally:
            if conn:
                conn.close()

    def initialize_schema(self) -> None:
        """
        Initialize database schema.

        Creates tables and indexes if they don't exist.
        """
        logger.info("Initializing database schema")

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create weather_measurements table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS weather_measurements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    -- Timestamp (Unix epoch seconds, indexed for time-series queries)
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

            # Create indexes for efficient querying
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON weather_measurements(timestamp DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_mac_address
                ON weather_measurements(mac_address)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_mac_timestamp
                ON weather_measurements(mac_address, timestamp DESC)
            """)

            # Create devices metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    mac_address TEXT PRIMARY KEY,
                    device_name TEXT,
                    location TEXT,
                    last_seen DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create schema version table for future migrations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Set initial schema version
            cursor.execute("""
                INSERT OR IGNORE INTO schema_version (version) VALUES (1)
            """)

            conn.commit()
            logger.info("Database schema initialized successfully")

    def insert_measurement(self, measurement: WeatherMeasurement) -> Optional[int]:
        """
        Insert a weather measurement into the database.

        Uses INSERT OR IGNORE to skip duplicates based on (timestamp, mac_address).

        Args:
            measurement: WeatherMeasurement instance

        Returns:
            Row ID if inserted, None if duplicate

        Raises:
            DatabaseError: If insert fails
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO weather_measurements (
                        timestamp, temp_outdoor, temp_indoor, feels_like, dew_point,
                        humidity_outdoor, humidity_indoor,
                        pressure_relative, pressure_absolute,
                        wind_speed, wind_gust, wind_direction, wind_gust_direction, max_daily_gust,
                        hourly_rain, daily_rain, weekly_rain, monthly_rain, yearly_rain,
                        solar_radiation, uv_index,
                        mac_address
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    measurement.timestamp,
                    measurement.temp_outdoor,
                    measurement.temp_indoor,
                    measurement.feels_like,
                    measurement.dew_point,
                    measurement.humidity_outdoor,
                    measurement.humidity_indoor,
                    measurement.pressure_relative,
                    measurement.pressure_absolute,
                    measurement.wind_speed,
                    measurement.wind_gust,
                    measurement.wind_direction,
                    measurement.wind_gust_direction,
                    measurement.max_daily_gust,
                    measurement.hourly_rain,
                    measurement.daily_rain,
                    measurement.weekly_rain,
                    measurement.monthly_rain,
                    measurement.yearly_rain,
                    measurement.solar_radiation,
                    measurement.uv_index,
                    measurement.mac_address,
                ))

                conn.commit()

                if cursor.lastrowid > 0:
                    logger.debug(f"Inserted measurement: {measurement.timestamp}")
                    return cursor.lastrowid
                else:
                    logger.debug(f"Duplicate measurement skipped: {measurement.timestamp}")
                    return None

            except sqlite3.IntegrityError as e:
                logger.warning(f"Integrity error inserting measurement: {e}")
                return None
            except sqlite3.Error as e:
                logger.error(f"Error inserting measurement: {e}")
                raise DatabaseError(f"Failed to insert measurement: {e}")

    def insert_measurements_batch(self, measurements: List[WeatherMeasurement]) -> int:
        """
        Insert multiple weather measurements in a batch.

        Args:
            measurements: List of WeatherMeasurement instances

        Returns:
            Number of measurements inserted (excluding duplicates)

        Raises:
            DatabaseError: If batch insert fails
        """
        if not measurements:
            return 0

        inserted_count = 0

        with self.get_connection() as conn:
            cursor = conn.cursor()

            try:
                for measurement in measurements:
                    cursor.execute("""
                        INSERT OR IGNORE INTO weather_measurements (
                            timestamp, temp_outdoor, temp_indoor, feels_like, dew_point,
                            humidity_outdoor, humidity_indoor,
                            pressure_relative, pressure_absolute,
                            wind_speed, wind_gust, wind_direction, wind_gust_direction, max_daily_gust,
                            hourly_rain, daily_rain, weekly_rain, monthly_rain, yearly_rain,
                            solar_radiation, uv_index,
                            mac_address
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        measurement.timestamp,
                        measurement.temp_outdoor,
                        measurement.temp_indoor,
                        measurement.feels_like,
                        measurement.dew_point,
                        measurement.humidity_outdoor,
                        measurement.humidity_indoor,
                        measurement.pressure_relative,
                        measurement.pressure_absolute,
                        measurement.wind_speed,
                        measurement.wind_gust,
                        measurement.wind_direction,
                        measurement.wind_gust_direction,
                        measurement.max_daily_gust,
                        measurement.hourly_rain,
                        measurement.daily_rain,
                        measurement.weekly_rain,
                        measurement.monthly_rain,
                        measurement.yearly_rain,
                        measurement.solar_radiation,
                        measurement.uv_index,
                        measurement.mac_address,
                    ))

                    if cursor.lastrowid > 0:
                        inserted_count += 1

                conn.commit()
                logger.info(f"Batch inserted {inserted_count}/{len(measurements)} measurements")

                return inserted_count

            except sqlite3.Error as e:
                logger.error(f"Error in batch insert: {e}")
                raise DatabaseError(f"Batch insert failed: {e}")

    def get_latest_timestamp(self, mac_address: str) -> Optional[int]:
        """
        Get the timestamp of the most recent measurement for a device.

        Args:
            mac_address: Device MAC address

        Returns:
            Unix epoch seconds of latest measurement or None if no data

        Raises:
            DatabaseError: If query fails
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    SELECT MAX(timestamp) as latest_timestamp
                    FROM weather_measurements
                    WHERE mac_address = ?
                """, (mac_address,))

                row = cursor.fetchone()

                if row and row['latest_timestamp']:
                    return row['latest_timestamp']
                else:
                    return None

            except sqlite3.Error as e:
                logger.error(f"Error getting latest timestamp: {e}")
                raise DatabaseError(f"Failed to get latest timestamp: {e}")

    def get_measurements(
        self,
        mac_address: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[WeatherMeasurement]:
        """
        Query weather measurements for a device within a time range.

        Args:
            mac_address: Device MAC address
            start_time: Start of time range as Unix epoch seconds (optional)
            end_time: End of time range as Unix epoch seconds (optional)
            limit: Maximum number of records to return (optional)

        Returns:
            List of WeatherMeasurement instances, ordered by timestamp descending

        Raises:
            DatabaseError: If query fails
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            try:
                # Build query dynamically based on parameters
                query = """
                    SELECT * FROM weather_measurements
                    WHERE mac_address = ?
                """
                params = [mac_address]

                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time)

                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(end_time)

                query += " ORDER BY timestamp DESC"

                if limit:
                    query += " LIMIT ?"
                    params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                # Convert rows to WeatherMeasurement objects
                measurements = []
                for row in rows:
                    measurement = WeatherMeasurement(
                        timestamp=row['timestamp'],
                        temp_outdoor=row['temp_outdoor'],
                        temp_indoor=row['temp_indoor'],
                        feels_like=row['feels_like'],
                        dew_point=row['dew_point'],
                        humidity_outdoor=row['humidity_outdoor'],
                        humidity_indoor=row['humidity_indoor'],
                        pressure_relative=row['pressure_relative'],
                        pressure_absolute=row['pressure_absolute'],
                        wind_speed=row['wind_speed'],
                        wind_gust=row['wind_gust'],
                        wind_direction=row['wind_direction'],
                        wind_gust_direction=row['wind_gust_direction'],
                        max_daily_gust=row['max_daily_gust'],
                        hourly_rain=row['hourly_rain'],
                        daily_rain=row['daily_rain'],
                        weekly_rain=row['weekly_rain'],
                        monthly_rain=row['monthly_rain'],
                        yearly_rain=row['yearly_rain'],
                        solar_radiation=row['solar_radiation'],
                        uv_index=row['uv_index'],
                        mac_address=row['mac_address'],
                    )
                    measurements.append(measurement)

                logger.debug(f"Retrieved {len(measurements)} measurements")
                return measurements

            except sqlite3.Error as e:
                logger.error(f"Error querying measurements: {e}")
                raise DatabaseError(f"Failed to query measurements: {e}")

    def get_record_count(self, mac_address: Optional[str] = None) -> int:
        """
        Get total number of records in database.

        Args:
            mac_address: Filter by device MAC address (optional)

        Returns:
            Number of records

        Raises:
            DatabaseError: If query fails
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            try:
                if mac_address:
                    cursor.execute("""
                        SELECT COUNT(*) as count
                        FROM weather_measurements
                        WHERE mac_address = ?
                    """, (mac_address,))
                else:
                    cursor.execute("""
                        SELECT COUNT(*) as count
                        FROM weather_measurements
                    """)

                row = cursor.fetchone()
                return row['count'] if row else 0

            except sqlite3.Error as e:
                logger.error(f"Error getting record count: {e}")
                raise DatabaseError(f"Failed to get record count: {e}")

    def update_device_metadata(
        self, mac_address: str, device_name: Optional[str] = None, location: Optional[str] = None
    ) -> None:
        """
        Update device metadata.

        Args:
            mac_address: Device MAC address
            device_name: Device name (optional)
            location: Device location (optional)

        Raises:
            DatabaseError: If update fails
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    INSERT INTO devices (mac_address, device_name, location, last_seen)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(mac_address) DO UPDATE SET
                        device_name = COALESCE(?, device_name),
                        location = COALESCE(?, location),
                        last_seen = ?
                """, (
                    mac_address, device_name, location, datetime.now(),
                    device_name, location, datetime.now()
                ))

                conn.commit()
                logger.debug(f"Updated metadata for device {mac_address}")

            except sqlite3.Error as e:
                logger.error(f"Error updating device metadata: {e}")
                raise DatabaseError(f"Failed to update device metadata: {e}")
