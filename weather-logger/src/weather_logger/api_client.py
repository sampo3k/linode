"""
Ambient Weather API client.
"""
import logging
import time
from typing import Dict, List, Optional

import requests

from .models import WeatherMeasurement


logger = logging.getLogger(__name__)


class AmbientWeatherAPIError(Exception):
    """Base exception for Ambient Weather API errors."""
    pass


class RateLimitError(AmbientWeatherAPIError):
    """Raised when API rate limit is exceeded."""
    pass


class AuthenticationError(AmbientWeatherAPIError):
    """Raised when API authentication fails."""
    pass


class AmbientWeatherClient:
    """
    Client for Ambient Weather API.

    Handles authentication, rate limiting, and data retrieval.
    API Documentation: https://ambientweather.docs.apiary.io/
    """

    BASE_URL = "https://rt.ambientweather.net/v1"

    def __init__(self, api_key: str, application_key: str):
        """
        Initialize Ambient Weather API client.

        Args:
            api_key: Your Ambient Weather API key
            application_key: Your Ambient Weather Application key
        """
        self.api_key = api_key
        self.application_key = application_key
        self.session = requests.Session()
        self._last_request_time = 0.0

        # Set default timeout for all requests
        self.timeout = 10

        logger.info("Initialized Ambient Weather API client")

    def get_devices(self) -> List[Dict]:
        """
        Get list of devices associated with the account.

        Returns:
            List of device dictionaries

        Raises:
            AmbientWeatherAPIError: If API request fails
        """
        logger.debug("Fetching device list")
        endpoint = "/devices"
        response = self._make_request(endpoint)

        devices = response if isinstance(response, list) else []
        logger.info(f"Retrieved {len(devices)} device(s)")

        return devices

    def get_device_data(
        self, mac_address: str, limit: int = 1, end_date: Optional[int] = None
    ) -> List[Dict]:
        """
        Get data for a specific device.

        Args:
            mac_address: Device MAC address
            limit: Number of records to retrieve (default 1, max 288)
            end_date: End date in milliseconds since epoch (optional)

        Returns:
            List of data dictionaries, most recent first

        Raises:
            AmbientWeatherAPIError: If API request fails
        """
        logger.debug(f"Fetching data for device {mac_address}, limit={limit}")

        endpoint = f"/devices/{mac_address}"
        params = {"limit": limit}

        if end_date:
            params["endDate"] = end_date

        response = self._make_request(endpoint, params)

        data = response if isinstance(response, list) else []
        logger.info(f"Retrieved {len(data)} record(s) for device {mac_address}")

        return data

    def get_latest_measurement(self, mac_address: str) -> Optional[WeatherMeasurement]:
        """
        Get the latest weather measurement for a device.

        Args:
            mac_address: Device MAC address

        Returns:
            WeatherMeasurement instance or None if no data

        Raises:
            AmbientWeatherAPIError: If API request fails
        """
        data = self.get_device_data(mac_address, limit=1)

        if not data:
            logger.warning(f"No data available for device {mac_address}")
            return None

        return WeatherMeasurement.from_api_response(data[0], mac_address)

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make an authenticated request to the Ambient Weather API.

        Args:
            endpoint: API endpoint (e.g., '/devices')
            params: Query parameters (optional)

        Returns:
            Response JSON data

        Raises:
            AmbientWeatherAPIError: If request fails
            RateLimitError: If rate limit is exceeded
            AuthenticationError: If authentication fails
        """
        # Enforce rate limiting
        self._enforce_rate_limit()

        # Prepare request
        url = f"{self.BASE_URL}{endpoint}"

        if params is None:
            params = {}

        # Add authentication parameters
        params["applicationKey"] = self.application_key
        params["apiKey"] = self.api_key

        logger.debug(f"Making request to {endpoint}")

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)

            # Handle different status codes
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                raise AuthenticationError(
                    "Authentication failed. Check your API key and application key."
                )
            elif response.status_code == 429:
                raise RateLimitError("API rate limit exceeded. Please wait before retrying.")
            else:
                error_msg = f"API request failed with status {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f": {error_detail}"
                except Exception:
                    error_msg += f": {response.text}"

                raise AmbientWeatherAPIError(error_msg)

        except requests.Timeout:
            logger.error(f"Request to {endpoint} timed out after {self.timeout}s")
            raise AmbientWeatherAPIError(f"Request timed out after {self.timeout}s")

        except requests.ConnectionError as e:
            logger.error(f"Connection error while accessing {endpoint}: {e}")
            raise AmbientWeatherAPIError(f"Connection error: {e}")

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise AmbientWeatherAPIError(f"Request failed: {e}")

    def _enforce_rate_limit(self) -> None:
        """
        Enforce API rate limit of 1 request per second.

        Sleeps if necessary to ensure at least 1 second between requests.
        """
        elapsed = time.time() - self._last_request_time

        if elapsed < 1.0:
            sleep_time = 1.0 - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.3f}s")
            time.sleep(sleep_time)

        self._last_request_time = time.time()

    def test_connection(self) -> bool:
        """
        Test API connection and authentication.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            devices = self.get_devices()
            logger.info(f"Connection test successful. Found {len(devices)} device(s).")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"AmbientWeatherClient(api_key=***REDACTED***)"
