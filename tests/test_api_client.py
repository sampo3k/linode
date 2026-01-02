"""
Tests for API client module.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from weather_logger.api_client import (
    AmbientWeatherClient,
    AmbientWeatherAPIError,
    RateLimitError,
    AuthenticationError
)


class TestAmbientWeatherClient:
    """Tests for AmbientWeatherClient class."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return AmbientWeatherClient(
            api_key="test_api_key",
            application_key="test_app_key"
        )

    @patch('weather_logger.api_client.requests.Session.get')
    def test_get_devices_success(self, mock_get, client):
        """Test successful device list retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"macAddress": "AA:BB:CC:DD:EE:FF", "info": {"name": "Weather Station"}}
        ]
        mock_get.return_value = mock_response

        devices = client.get_devices()

        assert len(devices) == 1
        assert devices[0]["macAddress"] == "AA:BB:CC:DD:EE:FF"

    @patch('weather_logger.api_client.requests.Session.get')
    def test_get_device_data_success(self, mock_get, client):
        """Test successful device data retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "dateutc": 1640000000000,
                "tempf": 72.5,
                "humidity": 50
            }
        ]
        mock_get.return_value = mock_response

        data = client.get_device_data("AA:BB:CC:DD:EE:FF", limit=1)

        assert len(data) == 1
        assert data[0]["tempf"] == 72.5
        assert data[0]["humidity"] == 50

    @patch('weather_logger.api_client.requests.Session.get')
    def test_authentication_error(self, mock_get, client):
        """Test authentication error handling."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        with pytest.raises(AuthenticationError, match="Authentication failed"):
            client.get_devices()

    @patch('weather_logger.api_client.requests.Session.get')
    def test_rate_limit_error(self, mock_get, client):
        """Test rate limit error handling."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        with pytest.raises(RateLimitError, match="rate limit exceeded"):
            client.get_devices()

    @patch('weather_logger.api_client.requests.Session.get')
    def test_get_latest_measurement(self, mock_get, client):
        """Test getting latest measurement."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "dateutc": 1640000000000,
                "tempf": 72.5,
                "humidity": 50
            }
        ]
        mock_get.return_value = mock_response

        measurement = client.get_latest_measurement("AA:BB:CC:DD:EE:FF")

        assert measurement is not None
        assert measurement.temp_outdoor == 72.5
        assert measurement.humidity_outdoor == 50
        assert measurement.mac_address == "AA:BB:CC:DD:EE:FF"

    def test_rate_limiting(self, client):
        """Test that rate limiting enforces 1 second delay."""
        import time

        # Set last request time to now
        client._last_request_time = time.time()

        # Enforce rate limit should sleep
        start = time.time()
        client._enforce_rate_limit()
        elapsed = time.time() - start

        # Should have slept for approximately 1 second
        assert elapsed >= 0.9  # Allow some tolerance
