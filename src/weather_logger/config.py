"""
Configuration management for Weather Logger.
Supports loading from YAML files and environment variables.
"""
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


class Config:
    """Configuration manager for Weather Logger."""

    def __init__(self, config_dict: Dict[str, Any]):
        """
        Initialize Config with a dictionary.

        Args:
            config_dict: Configuration dictionary
        """
        self._config = config_dict
        self.validate()

    @classmethod
    def load_from_file(cls, path: str = "config.yaml") -> "Config":
        """
        Load configuration from a YAML file.

        Args:
            path: Path to YAML configuration file

        Returns:
            Config instance

        Raises:
            ConfigError: If file cannot be read or parsed
        """
        config_path = Path(path)

        if not config_path.exists():
            raise ConfigError(f"Configuration file not found: {path}")

        try:
            with open(config_path, 'r') as f:
                config_dict = yaml.safe_load(f)

            if config_dict is None:
                raise ConfigError(f"Configuration file is empty: {path}")

            return cls(config_dict)
        except yaml.YAMLError as e:
            raise ConfigError(f"Failed to parse YAML configuration: {e}")
        except IOError as e:
            raise ConfigError(f"Failed to read configuration file: {e}")

    @classmethod
    def load_from_env(cls) -> "Config":
        """
        Load configuration from environment variables.

        Environment variables should be prefixed with WEATHER_LOGGER_
        and use underscores for nested keys.

        Example:
            WEATHER_LOGGER_AMBIENT_WEATHER_API_KEY=abc123
            WEATHER_LOGGER_DATABASE_PATH=data/weather.db

        Returns:
            Config instance
        """
        config_dict: Dict[str, Any] = {
            "ambient_weather": {},
            "database": {},
            "logging": {}
        }

        # Ambient Weather settings
        if api_key := os.getenv("WEATHER_LOGGER_AMBIENT_WEATHER_API_KEY"):
            config_dict["ambient_weather"]["api_key"] = api_key
        if app_key := os.getenv("WEATHER_LOGGER_AMBIENT_WEATHER_APPLICATION_KEY"):
            config_dict["ambient_weather"]["application_key"] = app_key
        if mac := os.getenv("WEATHER_LOGGER_AMBIENT_WEATHER_MAC_ADDRESS"):
            config_dict["ambient_weather"]["mac_address"] = mac
        if interval := os.getenv("WEATHER_LOGGER_AMBIENT_WEATHER_POLL_INTERVAL"):
            config_dict["ambient_weather"]["poll_interval"] = int(interval)

        # Database settings
        if db_path := os.getenv("WEATHER_LOGGER_DATABASE_PATH"):
            config_dict["database"]["path"] = db_path

        # Logging settings
        if log_level := os.getenv("WEATHER_LOGGER_LOGGING_LEVEL"):
            config_dict["logging"]["level"] = log_level
        if log_file := os.getenv("WEATHER_LOGGER_LOGGING_FILE"):
            config_dict["logging"]["file"] = log_file
        if log_format := os.getenv("WEATHER_LOGGER_LOGGING_FORMAT"):
            config_dict["logging"]["format"] = log_format

        return cls(config_dict)

    def validate(self) -> None:
        """
        Validate configuration values.

        Raises:
            ConfigError: If any required field is missing or invalid
        """
        # Validate ambient_weather section
        if "ambient_weather" not in self._config:
            raise ConfigError("Missing 'ambient_weather' section in configuration")

        ambient = self._config["ambient_weather"]

        if not ambient.get("api_key"):
            raise ConfigError("Missing required field: ambient_weather.api_key")
        if not ambient.get("application_key"):
            raise ConfigError("Missing required field: ambient_weather.application_key")
        if not ambient.get("mac_address"):
            raise ConfigError("Missing required field: ambient_weather.mac_address")

        # Validate MAC address format
        mac_address = ambient["mac_address"]
        if not self._is_valid_mac_address(mac_address):
            raise ConfigError(f"Invalid MAC address format: {mac_address}")

        # Validate poll interval
        poll_interval = ambient.get("poll_interval", 60)
        if not isinstance(poll_interval, int) or poll_interval < 60:
            raise ConfigError("poll_interval must be an integer >= 60 seconds")

        # Validate database section
        if "database" not in self._config:
            raise ConfigError("Missing 'database' section in configuration")

        db_path = self._config["database"].get("path")
        if not db_path:
            raise ConfigError("Missing required field: database.path")

        # Validate logging section (optional, with defaults)
        if "logging" in self._config:
            log_level = self._config["logging"].get("level", "INFO")
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if log_level.upper() not in valid_levels:
                raise ConfigError(f"Invalid log level: {log_level}. Must be one of {valid_levels}")

    @staticmethod
    def _is_valid_mac_address(mac: str) -> bool:
        """
        Validate MAC address format.

        Accepts formats: XX:XX:XX:XX:XX:XX or XXXXXXXXXXXX

        Args:
            mac: MAC address string

        Returns:
            True if valid, False otherwise
        """
        # Pattern with colons
        pattern1 = re.compile(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$')
        # Pattern without colons
        pattern2 = re.compile(r'^[0-9A-Fa-f]{12}$')

        return bool(pattern1.match(mac) or pattern2.match(mac))

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key: Configuration key (e.g., 'ambient_weather.api_key')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_ambient_weather_config(self) -> Dict[str, Any]:
        """Get ambient weather configuration section."""
        return self._config.get("ambient_weather", {})

    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration section."""
        return self._config.get("database", {})

    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration section with defaults."""
        defaults = {
            "level": "INFO",
            "file": "logs/weather_logger.log",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
        config = self._config.get("logging", {})
        return {**defaults, **config}

    def to_dict(self, sanitize: bool = True) -> Dict[str, Any]:
        """
        Export configuration as dictionary.

        Args:
            sanitize: If True, redact sensitive values (API keys)

        Returns:
            Configuration dictionary
        """
        if not sanitize:
            return self._config.copy()

        # Create a sanitized copy
        sanitized = self._config.copy()

        if "ambient_weather" in sanitized:
            ambient = sanitized["ambient_weather"].copy()
            if "api_key" in ambient:
                ambient["api_key"] = "***REDACTED***"
            if "application_key" in ambient:
                ambient["application_key"] = "***REDACTED***"
            sanitized["ambient_weather"] = ambient

        return sanitized
