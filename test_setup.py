#!/usr/bin/env python3
"""
Test script to validate configuration and API connectivity.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from weather_logger import (
    Config,
    AmbientWeatherClient,
    WeatherDatabase,
    ConfigError,
    AmbientWeatherAPIError
)
from weather_logger.utils import setup_logging


def test_configuration():
    """Test loading and validating configuration."""
    print("=" * 60)
    print("TEST 1: Configuration Loading")
    print("=" * 60)

    try:
        config = Config.load_from_file("config.yaml")
        print("✓ Configuration loaded successfully")

        # Display sanitized config
        print("\nConfiguration:")
        sanitized = config.to_dict(sanitize=True)
        print(f"  API Key: {sanitized['ambient_weather']['api_key']}")
        print(f"  Application Key: {sanitized['ambient_weather']['application_key']}")
        print(f"  MAC Address: {sanitized['ambient_weather']['mac_address']}")
        print(f"  Poll Interval: {sanitized['ambient_weather']['poll_interval']}s")
        print(f"  Database Path: {sanitized['database']['path']}")

        return config
    except ConfigError as e:
        print(f"✗ Configuration error: {e}")
        return None


def test_api_connection(config):
    """Test API connectivity and authentication."""
    print("\n" + "=" * 60)
    print("TEST 2: API Connection")
    print("=" * 60)

    try:
        # Create API client
        client = AmbientWeatherClient(
            api_key=config.get("ambient_weather.api_key"),
            application_key=config.get("ambient_weather.application_key")
        )

        print("Testing API connection...")

        # Get devices
        devices = client.get_devices()
        print(f"✓ API connection successful!")
        print(f"✓ Found {len(devices)} device(s)")

        # Display device info
        for i, device in enumerate(devices, 1):
            print(f"\nDevice {i}:")
            print(f"  MAC Address: {device.get('macAddress')}")
            if 'info' in device:
                print(f"  Name: {device['info'].get('name', 'N/A')}")
                print(f"  Location: {device['info'].get('location', 'N/A')}")

        return client, devices
    except AmbientWeatherAPIError as e:
        print(f"✗ API error: {e}")
        return None, None


def test_fetch_data(client, config):
    """Test fetching weather data."""
    print("\n" + "=" * 60)
    print("TEST 3: Fetching Weather Data")
    print("=" * 60)

    mac_address = config.get("ambient_weather.mac_address")
    print(f"Fetching latest data for device: {mac_address}")

    try:
        measurement = client.get_latest_measurement(mac_address)

        if measurement:
            print("✓ Successfully fetched weather data")
            print(f"\nLatest Measurement:")
            print(f"  Timestamp: {measurement.timestamp}")
            print(f"  Outdoor Temperature: {measurement.temp_outdoor}°F")
            print(f"  Indoor Temperature: {measurement.temp_indoor}°F")
            print(f"  Outdoor Humidity: {measurement.humidity_outdoor}%")
            print(f"  Indoor Humidity: {measurement.humidity_indoor}%")
            print(f"  Pressure: {measurement.pressure_relative} inHg")
            print(f"  Wind Speed: {measurement.wind_speed} mph")
            print(f"  Wind Direction: {measurement.wind_direction}°")

            if measurement.solar_radiation:
                print(f"  Solar Radiation: {measurement.solar_radiation} W/m²")
            if measurement.uv_index:
                print(f"  UV Index: {measurement.uv_index}")
            if measurement.daily_rain:
                print(f"  Daily Rain: {measurement.daily_rain} in")

            return measurement
        else:
            print("✗ No data available for this device")
            return None
    except AmbientWeatherAPIError as e:
        print(f"✗ Error fetching data: {e}")
        return None


def test_database(config, measurement):
    """Test database initialization and data insertion."""
    print("\n" + "=" * 60)
    print("TEST 4: Database Operations")
    print("=" * 60)

    try:
        # Initialize database
        db_path = config.get("database.path")
        db = WeatherDatabase(db_path)

        print(f"Initializing database at: {db_path}")
        db.initialize_schema()
        print("✓ Database schema initialized")

        # Check existing records
        count = db.get_record_count()
        print(f"✓ Current record count: {count}")

        if measurement:
            # Insert measurement
            print("\nInserting measurement into database...")
            row_id = db.insert_measurement(measurement)

            if row_id:
                print(f"✓ Measurement inserted (row ID: {row_id})")
            else:
                print("⚠ Measurement already exists (duplicate skipped)")

            # Get latest timestamp
            mac = config.get("ambient_weather.mac_address")
            latest = db.get_latest_timestamp(mac)
            print(f"✓ Latest timestamp in database: {latest}")

            # Get updated count
            new_count = db.get_record_count()
            print(f"✓ Total records in database: {new_count}")

        return True
    except Exception as e:
        print(f"✗ Database error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\nWeather Logger - Configuration and API Test")
    print("=" * 60)

    # Test 1: Configuration
    config = test_configuration()
    if not config:
        print("\n❌ Configuration test failed. Please fix config.yaml")
        return False

    # Setup logging
    log_config = config.get_logging_config()
    setup_logging(
        log_file=log_config['file'],
        log_level=log_config['level'],
        log_format=log_config['format']
    )

    # Test 2: API Connection
    client, devices = test_api_connection(config)
    if not client:
        print("\n❌ API connection test failed. Check your credentials.")
        return False

    # Test 3: Fetch Data
    measurement = test_fetch_data(client, config)
    if not measurement:
        print("\n⚠ Warning: Could not fetch weather data, but API connection works.")

    # Test 4: Database
    db_success = test_database(config, measurement)

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("✓ Configuration: PASS")
    print("✓ API Connection: PASS")
    print(f"{'✓' if measurement else '⚠'} Data Fetch: {'PASS' if measurement else 'WARNING'}")
    print(f"{'✓' if db_success else '✗'} Database: {'PASS' if db_success else 'FAIL'}")

    if measurement and db_success:
        print("\n🎉 All tests passed! Your setup is working correctly.")
        print("\nNext steps:")
        print("  1. Review the data above to ensure it looks correct")
        print("  2. Ready to implement Phase 3 (Data Collection Service)")
    elif db_success:
        print("\n⚠ Setup mostly working, but no weather data available.")
        print("   This might be normal if your device hasn't reported recently.")
    else:
        print("\n❌ Some tests failed. Please review the errors above.")

    return measurement is not None and db_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
