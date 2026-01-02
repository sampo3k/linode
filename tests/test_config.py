"""
Tests for config module.
"""
import pytest
from pathlib import Path
from weather_logger.config import Config, ConfigError


class TestConfig:
    """Tests for Config class."""

    def test_load_from_valid_file(self, tmp_path):
        """Test loading configuration from a valid YAML file."""
        # Create a temporary config file
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ambient_weather:
  api_key: "test_api_key"
  application_key: "test_app_key"
  mac_address: "AA:BB:CC:DD:EE:FF"
  poll_interval: 60

database:
  path: "data/weather.db"

logging:
  level: "INFO"
  file: "logs/weather_logger.log"
        """)

        config = Config.load_from_file(str(config_file))

        assert config.get("ambient_weather.api_key") == "test_api_key"
        assert config.get("ambient_weather.application_key") == "test_app_key"
        assert config.get("ambient_weather.mac_address") == "AA:BB:CC:DD:EE:FF"
        assert config.get("database.path") == "data/weather.db"

    def test_load_from_missing_file(self):
        """Test that loading from a missing file raises ConfigError."""
        with pytest.raises(ConfigError, match="Configuration file not found"):
            Config.load_from_file("nonexistent.yaml")

    def test_validation_missing_api_key(self):
        """Test validation fails when API key is missing."""
        config_dict = {
            "ambient_weather": {
                "application_key": "test_app_key",
                "mac_address": "AA:BB:CC:DD:EE:FF"
            },
            "database": {"path": "data/weather.db"}
        }

        with pytest.raises(ConfigError, match="api_key"):
            Config(config_dict)

    def test_validation_invalid_mac_address(self):
        """Test validation fails with invalid MAC address."""
        config_dict = {
            "ambient_weather": {
                "api_key": "test_api_key",
                "application_key": "test_app_key",
                "mac_address": "INVALID_MAC"
            },
            "database": {"path": "data/weather.db"}
        }

        with pytest.raises(ConfigError, match="Invalid MAC address"):
            Config(config_dict)

    def test_validation_invalid_poll_interval(self):
        """Test validation fails with poll interval < 60."""
        config_dict = {
            "ambient_weather": {
                "api_key": "test_api_key",
                "application_key": "test_app_key",
                "mac_address": "AA:BB:CC:DD:EE:FF",
                "poll_interval": 30
            },
            "database": {"path": "data/weather.db"}
        }

        with pytest.raises(ConfigError, match="poll_interval"):
            Config(config_dict)

    def test_get_with_default(self):
        """Test getting config value with default."""
        config_dict = {
            "ambient_weather": {
                "api_key": "test_api_key",
                "application_key": "test_app_key",
                "mac_address": "AA:BB:CC:DD:EE:FF"
            },
            "database": {"path": "data/weather.db"}
        }

        config = Config(config_dict)
        assert config.get("nonexistent.key", "default_value") == "default_value"

    def test_to_dict_sanitized(self):
        """Test that to_dict redacts sensitive information."""
        config_dict = {
            "ambient_weather": {
                "api_key": "test_api_key",
                "application_key": "test_app_key",
                "mac_address": "AA:BB:CC:DD:EE:FF"
            },
            "database": {"path": "data/weather.db"}
        }

        config = Config(config_dict)
        sanitized = config.to_dict(sanitize=True)

        assert sanitized["ambient_weather"]["api_key"] == "***REDACTED***"
        assert sanitized["ambient_weather"]["application_key"] == "***REDACTED***"
        assert sanitized["ambient_weather"]["mac_address"] == "AA:BB:CC:DD:EE:FF"
