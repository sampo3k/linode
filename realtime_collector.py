#!/usr/bin/env python3
"""
Weather data realtime collector service using Ambient Weather WebSocket API.

Uses Socket.IO to receive data as soon as it's published by the weather station
(typically once per minute) rather than polling the REST API.
"""
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

import socketio

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from weather_logger import (
    Config,
    ConfigError,
    WeatherDatabase,
    DatabaseError,
    WeatherMeasurement,
)
from weather_logger.utils import setup_logging


logger = logging.getLogger(__name__)


class RealtimeWeatherCollector:
    """
    Realtime weather data collection service using WebSocket API.

    Connects to Ambient Weather's Socket.IO endpoint and receives
    data updates in realtime as they're published by the weather station.
    """

    REALTIME_URL = "https://rt2.ambientweather.net"

    def __init__(self, config: Config):
        """
        Initialize the realtime weather collector.

        Args:
            config: Configuration instance
        """
        self.config = config
        self.running = False
        self.mac_address = config.get("ambient_weather.mac_address")
        self.api_key = config.get("ambient_weather.api_key")
        self.application_key = config.get("ambient_weather.application_key")

        # Statistics
        self.connection_count = 0
        self.data_received_count = 0
        self.data_stored_count = 0
        self.duplicate_count = 0
        self.error_count = 0

        # Initialize database
        db_path = config.get("database.path")
        self.database = WeatherDatabase(db_path)
        self.database.initialize_schema()

        # Initialize Socket.IO client
        self.sio = socketio.Client(
            logger=False,
            engineio_logger=False,
            reconnection=True,
            reconnection_attempts=0,  # Infinite retries
            reconnection_delay=1,
            reconnection_delay_max=10,
        )

        # Register event handlers
        self._register_handlers()

        logger.info(f"Realtime collector initialized for device {self.mac_address}")
        logger.info(f"Realtime endpoint: {self.REALTIME_URL}")

    def _register_handlers(self):
        """Register Socket.IO event handlers."""

        @self.sio.event
        def connect():
            """Handle connection to Socket.IO server."""
            self.connection_count += 1
            logger.info(f"Connected to Ambient Weather realtime API (connection #{self.connection_count})")

            # Subscribe to device data
            try:
                logger.info(f"Subscribing to device {self.mac_address}...")
                subscribe_data = {"apiKeys": [self.api_key]}
                logger.debug(f"Subscribe payload: {subscribe_data}")
                self.sio.emit("subscribe", subscribe_data)
                logger.info("Subscription request sent")
            except Exception as e:
                logger.error(f"Failed to subscribe: {e}")
                self.error_count += 1

        @self.sio.event
        def disconnect():
            """Handle disconnection from Socket.IO server."""
            logger.warning("Disconnected from Ambient Weather realtime API")

        @self.sio.event
        def connect_error(data):
            """Handle connection errors."""
            logger.error(f"Connection error: {data}")
            self.error_count += 1

        @self.sio.event
        def subscribed(data):
            """Handle subscription confirmation."""
            logger.info(f"Subscription confirmed: {data}")
            logger.info("Waiting for realtime data updates...")

        @self.sio.event
        def data(data):
            """Handle incoming weather data."""
            self.data_received_count += 1

            try:
                # Data is the weather measurement itself
                if not isinstance(data, dict):
                    logger.warning(f"Unexpected data format: {type(data)}, value: {data}")
                    return

                # Check if this is for our device
                mac_in_data = data.get('macAddress', '')
                if mac_in_data.upper() != self.mac_address.upper():
                    logger.debug(f"Data for different device: {mac_in_data}")
                    return

                logger.info(f"Received realtime data update for {mac_in_data}")

                # Parse and store the measurement
                self._process_measurement(data)

            except Exception as e:
                logger.exception(f"Error processing data: {e}")
                self.error_count += 1

        @self.sio.on('*')
        def catch_all(event, data):
            """Catch all events for debugging."""
            logger.debug(f"Received event '{event}': {data}")

    def _process_measurement(self, data: dict):
        """
        Process and store a weather measurement.

        Args:
            data: Weather data from Socket.IO event
        """
        try:
            # Convert to WeatherMeasurement
            measurement = WeatherMeasurement.from_api_response(data, self.mac_address)

            # Log the measurement
            logger.info(
                f"Received realtime update: {measurement.timestamp}, "
                f"temp={measurement.temp_outdoor}°F, "
                f"humidity={measurement.humidity_outdoor}%"
            )

            # Insert into database
            row_id = self.database.insert_measurement(measurement)

            if row_id:
                self.data_stored_count += 1
                logger.info(
                    f"Stored measurement in database (row ID: {row_id}) "
                    f"[Total stored: {self.data_stored_count}]"
                )

                # Update device metadata
                self.database.update_device_metadata(
                    mac_address=self.mac_address,
                    device_name="Oak",
                )
            else:
                self.duplicate_count += 1
                logger.debug(
                    f"Duplicate measurement skipped "
                    f"[Total duplicates: {self.duplicate_count}]"
                )

            # Log statistics every 10 updates
            if self.data_received_count % 10 == 0:
                self._log_statistics()

        except DatabaseError as e:
            logger.error(f"Database error: {e}")
            self.error_count += 1

        except Exception as e:
            logger.exception(f"Unexpected error processing measurement: {e}")
            self.error_count += 1

    def _log_statistics(self):
        """Log collection statistics."""
        total_records = self.database.get_record_count(self.mac_address)
        logger.info(
            f"Statistics: Connections={self.connection_count}, "
            f"Received={self.data_received_count}, "
            f"Stored={self.data_stored_count}, "
            f"Duplicates={self.duplicate_count}, "
            f"Errors={self.error_count}, "
            f"Total in DB={total_records}"
        )

    def connect(self):
        """Connect to the realtime API."""
        try:
            # Build URL with required query parameters
            url = f"{self.REALTIME_URL}/?api=1&applicationKey={self.application_key}"
            logger.info(f"Connecting to {self.REALTIME_URL}...")
            self.sio.connect(
                url,
                transports=["websocket", "polling"],
            )
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    def run(self):
        """
        Run the realtime collection service.

        Maintains WebSocket connection and processes data updates.
        """
        self.running = True
        logger.info("Realtime weather collector service started")

        # Get initial record count
        initial_count = self.database.get_record_count(self.mac_address)
        logger.info(f"Starting with {initial_count} existing records")

        # Connect to realtime API
        if not self.connect():
            logger.error("Failed to establish initial connection")
            return

        # Keep running until stopped
        try:
            while self.running:
                if not self.sio.connected:
                    logger.warning("Not connected, attempting to reconnect...")
                    time.sleep(5)
                    if self.running:
                        self.connect()
                else:
                    time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            logger.exception(f"Unexpected error in main loop: {e}")
        finally:
            self.stop()

    def stop(self):
        """Stop the collection service gracefully."""
        self.running = False
        logger.info("Stopping realtime collector...")

        # Disconnect from Socket.IO
        if self.sio.connected:
            try:
                self.sio.disconnect()
                logger.info("Disconnected from realtime API")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")

        # Final statistics
        self._log_statistics()
        logger.info("Realtime weather collector service stopped")


def setup_signal_handlers(collector: RealtimeWeatherCollector):
    """
    Setup signal handlers for graceful shutdown.

    Args:
        collector: RealtimeWeatherCollector instance
    """
    def signal_handler(signum, frame):
        """Handle shutdown signals."""
        signal_name = signal.Signals(signum).name
        logger.info(f"Received {signal_name} signal")
        collector.stop()
        sys.exit(0)

    # Handle SIGINT (Ctrl+C) and SIGTERM (Docker stop)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.debug("Signal handlers registered")


def main():
    """Main entry point for the realtime collector service."""
    print("Weather Logger - Realtime Data Collection Service")
    print("=" * 60)
    print("Using Ambient Weather Realtime API (WebSocket)")
    print("=" * 60)

    # Load configuration
    try:
        config = Config.load_from_file("config.yaml")
        logger.info("Configuration loaded successfully")
    except ConfigError as e:
        print(f"Configuration error: {e}")
        return 1

    # Setup logging
    log_config = config.get_logging_config()
    setup_logging(
        log_file=log_config["file"],
        log_level=log_config["level"],
        log_format=log_config["format"],
    )

    logger.info("=" * 60)
    logger.info("Weather Logger - Realtime Data Collection Service")
    logger.info("=" * 60)

    # Create collector
    try:
        collector = RealtimeWeatherCollector(config)
    except Exception as e:
        logger.exception(f"Failed to initialize collector: {e}")
        return 1

    # Setup signal handlers
    setup_signal_handlers(collector)

    print("\nRealtime collector is running. Press Ctrl+C to stop.")
    print("Waiting for weather station updates...")
    print(f"Logs: {log_config['file']}")
    print()

    # Run collector
    try:
        collector.run()
        return 0
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
