"""
Tests for database module.
"""
import pytest
from datetime import datetime
from pathlib import Path
from weather_logger.database import WeatherDatabase, DatabaseError
from weather_logger.models import WeatherMeasurement


class TestWeatherDatabase:
    """Tests for WeatherDatabase class."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a test database."""
        db_path = tmp_path / "test_weather.db"
        database = WeatherDatabase(str(db_path))
        database.initialize_schema()
        return database

    @pytest.fixture
    def sample_measurement(self):
        """Create a sample weather measurement."""
        return WeatherMeasurement(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            temp_outdoor=72.5,
            temp_indoor=70.0,
            humidity_outdoor=50,
            humidity_indoor=45,
            pressure_relative=29.92,
            wind_speed=5.0,
            mac_address="AA:BB:CC:DD:EE:FF"
        )

    def test_initialize_schema(self, tmp_path):
        """Test database schema initialization."""
        db_path = tmp_path / "test_weather.db"
        database = WeatherDatabase(str(db_path))
        database.initialize_schema()

        # Verify database file was created
        assert db_path.exists()

        # Verify tables exist
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='weather_measurements'
            """)
            assert cursor.fetchone() is not None

    def test_insert_measurement(self, db, sample_measurement):
        """Test inserting a measurement."""
        row_id = db.insert_measurement(sample_measurement)

        assert row_id is not None
        assert row_id > 0

        # Verify it was inserted
        count = db.get_record_count()
        assert count == 1

    def test_insert_duplicate_measurement(self, db, sample_measurement):
        """Test that duplicate measurements are ignored."""
        # Insert first time
        row_id1 = db.insert_measurement(sample_measurement)
        assert row_id1 is not None

        # Insert duplicate (same timestamp and MAC)
        row_id2 = db.insert_measurement(sample_measurement)
        assert row_id2 is None

        # Should still only have 1 record
        count = db.get_record_count()
        assert count == 1

    def test_get_latest_timestamp(self, db, sample_measurement):
        """Test getting latest timestamp."""
        # Initially, no data
        latest = db.get_latest_timestamp("AA:BB:CC:DD:EE:FF")
        assert latest is None

        # Insert measurement
        db.insert_measurement(sample_measurement)

        # Now should return the timestamp
        latest = db.get_latest_timestamp("AA:BB:CC:DD:EE:FF")
        assert latest is not None
        assert latest == sample_measurement.timestamp

    def test_get_measurements(self, db, sample_measurement):
        """Test querying measurements."""
        # Insert a measurement
        db.insert_measurement(sample_measurement)

        # Query it back
        measurements = db.get_measurements("AA:BB:CC:DD:EE:FF")

        assert len(measurements) == 1
        assert measurements[0].temp_outdoor == 72.5
        assert measurements[0].humidity_outdoor == 50

    def test_get_measurements_with_time_range(self, db):
        """Test querying measurements with time range."""
        # Insert measurements at different times
        m1 = WeatherMeasurement(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            temp_outdoor=70.0,
            mac_address="AA:BB:CC:DD:EE:FF"
        )
        m2 = WeatherMeasurement(
            timestamp=datetime(2024, 1, 1, 13, 0, 0),
            temp_outdoor=75.0,
            mac_address="AA:BB:CC:DD:EE:FF"
        )
        m3 = WeatherMeasurement(
            timestamp=datetime(2024, 1, 1, 14, 0, 0),
            temp_outdoor=80.0,
            mac_address="AA:BB:CC:DD:EE:FF"
        )

        db.insert_measurement(m1)
        db.insert_measurement(m2)
        db.insert_measurement(m3)

        # Query with time range
        measurements = db.get_measurements(
            "AA:BB:CC:DD:EE:FF",
            start_time=datetime(2024, 1, 1, 12, 30, 0),
            end_time=datetime(2024, 1, 1, 14, 30, 0)
        )

        # Should only get m2 and m3
        assert len(measurements) == 2
        temps = sorted([m.temp_outdoor for m in measurements])
        assert temps == [75.0, 80.0]

    def test_batch_insert(self, db):
        """Test batch inserting measurements."""
        measurements = [
            WeatherMeasurement(
                timestamp=datetime(2024, 1, 1, 12, i, 0),
                temp_outdoor=70.0 + i,
                mac_address="AA:BB:CC:DD:EE:FF"
            )
            for i in range(5)
        ]

        count = db.insert_measurements_batch(measurements)

        assert count == 5

        # Verify all were inserted
        total = db.get_record_count()
        assert total == 5

    def test_get_record_count_by_mac(self, db):
        """Test getting record count filtered by MAC address."""
        # Insert measurements for two different devices
        m1 = WeatherMeasurement(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            temp_outdoor=70.0,
            mac_address="AA:BB:CC:DD:EE:FF"
        )
        m2 = WeatherMeasurement(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            temp_outdoor=75.0,
            mac_address="11:22:33:44:55:66"
        )

        db.insert_measurement(m1)
        db.insert_measurement(m2)

        # Total count
        total = db.get_record_count()
        assert total == 2

        # Count for specific device
        count = db.get_record_count("AA:BB:CC:DD:EE:FF")
        assert count == 1
