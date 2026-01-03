"""
Data models for Weather Logger.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
import time


@dataclass
class WeatherMeasurement:
    """
    Represents a single weather measurement from an Ambient Weather station.

    All sensor fields are optional as not all weather stations have all sensors.
    """

    # Timestamp of the measurement (Unix epoch seconds)
    timestamp: int

    # Temperature fields (Fahrenheit)
    temp_outdoor: Optional[float] = None
    temp_indoor: Optional[float] = None
    feels_like: Optional[float] = None
    dew_point: Optional[float] = None

    # Humidity fields (percentage)
    humidity_outdoor: Optional[int] = None
    humidity_indoor: Optional[int] = None

    # Pressure fields (inHg)
    pressure_relative: Optional[float] = None
    pressure_absolute: Optional[float] = None

    # Wind fields
    wind_speed: Optional[float] = None  # mph
    wind_gust: Optional[float] = None  # mph
    wind_direction: Optional[int] = None  # degrees
    wind_gust_direction: Optional[int] = None  # degrees
    max_daily_gust: Optional[float] = None  # mph

    # Rain fields (inches)
    hourly_rain: Optional[float] = None
    daily_rain: Optional[float] = None
    weekly_rain: Optional[float] = None
    monthly_rain: Optional[float] = None
    yearly_rain: Optional[float] = None

    # Solar/UV fields
    solar_radiation: Optional[float] = None  # W/m^2
    uv_index: Optional[int] = None

    # Device information
    mac_address: str = ""

    @classmethod
    def from_api_response(cls, data: Dict, mac_address: str) -> "WeatherMeasurement":
        """
        Create a WeatherMeasurement from Ambient Weather API JSON response.

        Args:
            data: Dictionary from API response
            mac_address: Device MAC address

        Returns:
            WeatherMeasurement instance
        """
        # Parse timestamp (API returns milliseconds since epoch)
        timestamp_ms = data.get("dateutc", data.get("date"))
        if timestamp_ms:
            # Convert milliseconds to seconds
            timestamp = int(timestamp_ms // 1000)
        else:
            # Current Unix epoch seconds
            timestamp = int(time.time())

        return cls(
            timestamp=timestamp,
            # Temperature fields
            temp_outdoor=data.get("tempf"),
            temp_indoor=data.get("tempinf"),
            feels_like=data.get("feelsLike"),
            dew_point=data.get("dewPoint"),
            # Humidity fields
            humidity_outdoor=data.get("humidity"),
            humidity_indoor=data.get("humidityin"),
            # Pressure fields
            pressure_relative=data.get("baromrelin"),
            pressure_absolute=data.get("baromabsin"),
            # Wind fields
            wind_speed=data.get("windspeedmph"),
            wind_gust=data.get("windgustmph"),
            wind_direction=data.get("winddir"),
            wind_gust_direction=data.get("windgustdir"),
            max_daily_gust=data.get("maxdailygust"),
            # Rain fields
            hourly_rain=data.get("hourlyrainin"),
            daily_rain=data.get("dailyrainin"),
            weekly_rain=data.get("weeklyrainin"),
            monthly_rain=data.get("monthlyrainin"),
            yearly_rain=data.get("yearlyrainin"),
            # Solar/UV fields
            solar_radiation=data.get("solarradiation"),
            uv_index=data.get("uv"),
            # Device info
            mac_address=mac_address,
        )

    def to_dict(self) -> Dict:
        """
        Convert WeatherMeasurement to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "timestamp": self.timestamp,
            "temp_outdoor": self.temp_outdoor,
            "temp_indoor": self.temp_indoor,
            "feels_like": self.feels_like,
            "dew_point": self.dew_point,
            "humidity_outdoor": self.humidity_outdoor,
            "humidity_indoor": self.humidity_indoor,
            "pressure_relative": self.pressure_relative,
            "pressure_absolute": self.pressure_absolute,
            "wind_speed": self.wind_speed,
            "wind_gust": self.wind_gust,
            "wind_direction": self.wind_direction,
            "wind_gust_direction": self.wind_gust_direction,
            "max_daily_gust": self.max_daily_gust,
            "hourly_rain": self.hourly_rain,
            "daily_rain": self.daily_rain,
            "weekly_rain": self.weekly_rain,
            "monthly_rain": self.monthly_rain,
            "yearly_rain": self.yearly_rain,
            "solar_radiation": self.solar_radiation,
            "uv_index": self.uv_index,
            "mac_address": self.mac_address,
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        # Convert epoch to human-readable format for debugging
        timestamp_iso = datetime.fromtimestamp(self.timestamp).isoformat()
        return (
            f"WeatherMeasurement("
            f"timestamp={self.timestamp} ({timestamp_iso}), "
            f"temp_outdoor={self.temp_outdoor}, "
            f"humidity={self.humidity_outdoor}, "
            f"mac={self.mac_address})"
        )
