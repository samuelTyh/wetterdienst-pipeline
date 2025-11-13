"""Database schema definitions and data models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PostalCode(BaseModel):
    """Postal code model."""

    plz: str = Field(..., description="Postal code")
    note: str = Field(default="", description="Additional notes")
    geometry: str = Field(..., description="Geometry as WKT or GeoJSON string")
    centroid_lon: float = Field(..., description="Centroid longitude")
    centroid_lat: float = Field(..., description="Centroid latitude")
    ingested_at: datetime = Field(default_factory=datetime.now, description="Ingestion timestamp")


class WeatherStation(BaseModel):
    """Weather station model (from BrightSky sources)."""

    id: int = Field(..., description="Source ID from BrightSky")
    dwd_station_id: str = Field(..., description="DWD station identifier")
    wmo_station_id: str = Field(..., description="WMO station identifier")
    station_name: str = Field(..., description="Human-readable station name")
    observation_type: str = Field(
        ..., description="Type: forecast, observation, historical, current, synop"
    )
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    height: float = Field(..., description="Station elevation in meters")
    distance: float | None = Field(None, description="Distance from query point")
    first_record: datetime = Field(..., description="First available record timestamp")
    last_record: datetime = Field(..., description="Last available record timestamp")
    ingested_at: datetime = Field(default_factory=datetime.now, description="Ingestion timestamp")


class WeatherObservationSynop(BaseModel):
    """SYNOP weather observation model (10-minute resolution from /current_weather)."""

    source_id: int = Field(..., description="Reference to weather_stations.id")
    timestamp: datetime = Field(..., description="Observation timestamp")
    cloud_cover: float | None = Field(None, description="Cloud cover percentage (0-100)")
    condition: str | None = Field(None, description="Weather condition")
    dew_point: float | None = Field(None, description="Dew point in °C")
    icon: str | None = Field(None, description="Icon identifier")
    pressure_msl: float | None = Field(None, description="Mean sea level pressure in hPa")
    relative_humidity: float | None = Field(
        None, description="Relative humidity percentage (0-100)"
    )
    temperature: float | None = Field(None, description="Temperature in °C")
    visibility: float | None = Field(None, description="Visibility in meters")
    precipitation_10: float | None = Field(None, description="Precipitation in last 10 min (mm)")
    precipitation_30: float | None = Field(None, description="Precipitation in last 30 min (mm)")
    precipitation_60: float | None = Field(None, description="Precipitation in last 60 min (mm)")
    solar_10: float | None = Field(None, description="Solar radiation in last 10 min (W/m²)")
    solar_30: float | None = Field(None, description="Solar radiation in last 30 min (W/m²)")
    solar_60: float | None = Field(None, description="Solar radiation in last 60 min (W/m²)")
    sunshine_30: float | None = Field(None, description="Sunshine in last 30 min (minutes)")
    sunshine_60: float | None = Field(None, description="Sunshine in last 60 min (minutes)")
    wind_direction_10: float | None = Field(None, description="Wind direction in degrees (0-360)")
    wind_direction_30: float | None = Field(None, description="Wind direction in degrees (0-360)")
    wind_direction_60: float | None = Field(None, description="Wind direction in degrees (0-360)")
    wind_speed_10: float | None = Field(None, description="Wind speed in last 10 min (km/h)")
    wind_speed_30: float | None = Field(None, description="Wind speed in last 30 min (km/h)")
    wind_speed_60: float | None = Field(None, description="Wind speed in last 60 min (km/h)")
    wind_gust_direction_10: float | None = Field(None, description="Wind gust direction in degrees")
    wind_gust_direction_30: float | None = Field(None, description="Wind gust direction in degrees")
    wind_gust_direction_60: float | None = Field(None, description="Wind gust direction in degrees")
    wind_gust_speed_10: float | None = Field(None, description="Wind gust speed in km/h")
    wind_gust_speed_30: float | None = Field(None, description="Wind gust speed in km/h")
    wind_gust_speed_60: float | None = Field(None, description="Wind gust speed in km/h")
    ingested_at: datetime = Field(default_factory=datetime.now, description="Ingestion timestamp")


class WeatherObservation(BaseModel):
    """Hourly weather observation model (for historical data from /weather)."""

    source_id: int = Field(..., description="Reference to weather_stations.id")
    timestamp: datetime = Field(..., description="Observation timestamp")
    cloud_cover: float | None = Field(None, description="Cloud cover percentage (0-100)")
    condition: str | None = Field(None, description="Weather condition")
    dew_point: float | None = Field(None, description="Dew point in °C")
    icon: str | None = Field(None, description="Icon identifier")
    precipitation: float | None = Field(None, description="Precipitation in mm (hourly)")
    precipitation_probability: float | None = Field(
        None, description="Precipitation probability (0-100)"
    )
    precipitation_probability_6h: float | None = Field(
        None, description="6h precipitation probability"
    )
    pressure_msl: float | None = Field(None, description="Mean sea level pressure in hPa")
    relative_humidity: float | None = Field(
        None, description="Relative humidity percentage (0-100)"
    )
    sunshine: float | None = Field(None, description="Sunshine duration in minutes (hourly)")
    temperature: float | None = Field(None, description="Temperature in °C")
    visibility: float | None = Field(None, description="Visibility in meters")
    wind_direction: float | None = Field(None, description="Wind direction in degrees (0-360)")
    wind_speed: float | None = Field(None, description="Wind speed in km/h")
    wind_gust_direction: float | None = Field(None, description="Wind gust direction in degrees")
    wind_gust_speed: float | None = Field(None, description="Wind gust speed in km/h")
    ingested_at: datetime = Field(default_factory=datetime.now, description="Ingestion timestamp")


class WeatherForecast(BaseModel):
    """Weather forecast model."""

    source_id: int = Field(..., description="Reference to weather_stations.id")
    timestamp: datetime = Field(..., description="Forecast timestamp")
    cloud_cover: float | None = Field(None, description="Cloud cover percentage (0-100)")
    condition: str | None = Field(None, description="Weather condition")
    dew_point: float | None = Field(None, description="Dew point in °C")
    icon: str | None = Field(None, description="Icon identifier")
    precipitation: float | None = Field(None, description="Precipitation in mm")
    precipitation_probability: float | None = Field(
        None, description="Precipitation probability (0-100)"
    )
    precipitation_probability_6h: float | None = Field(
        None, description="6h precipitation probability"
    )
    pressure_msl: float | None = Field(None, description="Mean sea level pressure in hPa")
    relative_humidity: float | None = Field(
        None, description="Relative humidity percentage (0-100)"
    )
    sunshine: float | None = Field(None, description="Sunshine duration in minutes")
    temperature: float | None = Field(None, description="Temperature in °C")
    visibility: float | None = Field(None, description="Visibility in meters")
    wind_direction: float | None = Field(None, description="Wind direction in degrees (0-360)")
    wind_speed: float | None = Field(None, description="Wind speed in km/h")
    wind_gust_direction: float | None = Field(None, description="Wind gust direction in degrees")
    wind_gust_speed: float | None = Field(None, description="Wind gust speed in km/h")
    forecast_created_at: datetime = Field(..., description="When this forecast was issued")
    ingested_at: datetime = Field(default_factory=datetime.now, description="Ingestion timestamp")


class ObservationByPostalCode(BaseModel):
    """Cleaned observation per postal code model."""

    plz: str = Field(..., description="Postal code")
    timestamp: datetime = Field(..., description="Observation timestamp")
    temperature: float | None = Field(None, description="Temperature in °C")
    precipitation: float | None = Field(None, description="Precipitation in mm")
    relative_humidity: float | None = Field(None, description="Relative humidity percentage")
    wind_speed: float | None = Field(None, description="Wind speed in km/h")
    wind_direction: float | None = Field(None, description="Wind direction in degrees")
    pressure_msl: float | None = Field(None, description="Mean sea level pressure in hPa")
    cloud_cover: float | None = Field(None, description="Cloud cover percentage")
    sunshine: float | None = Field(None, description="Sunshine duration in minutes")
    condition: str | None = Field(None, description="Weather condition")
    num_stations: int = Field(..., description="Number of stations used for aggregation")
    data_quality_score: float = Field(..., description="Data quality score (0-1)")
    is_validated: bool = Field(..., description="Whether data passed validation")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")


class ForecastByPostalCode(BaseModel):
    """Cleaned forecast per postal code model."""

    plz: str = Field(..., description="Postal code")
    timestamp: datetime = Field(..., description="Forecast timestamp")
    forecast_created_at: datetime = Field(..., description="When forecast was issued")
    temperature: float | None = Field(None, description="Temperature in °C")
    precipitation: float | None = Field(None, description="Precipitation in mm")
    precipitation_probability: float | None = Field(None, description="Precipitation probability")
    relative_humidity: float | None = Field(None, description="Relative humidity percentage")
    wind_speed: float | None = Field(None, description="Wind speed in km/h")
    wind_direction: float | None = Field(None, description="Wind direction in degrees")
    pressure_msl: float | None = Field(None, description="Mean sea level pressure in hPa")
    cloud_cover: float | None = Field(None, description="Cloud cover percentage")
    sunshine: float | None = Field(None, description="Sunshine duration in minutes")
    condition: str | None = Field(None, description="Weather condition")
    num_stations: int = Field(..., description="Number of stations used for aggregation")
    data_quality_score: float = Field(..., description="Data quality score (0-1)")
    is_validated: bool = Field(..., description="Whether data passed validation")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")


def model_to_dict(model: BaseModel) -> dict[str, Any]:
    """Convert Pydantic model to dictionary for database insertion.

    Args:
        model: Pydantic model instance

    Returns:
        Dictionary representation
    """
    return model.model_dump()


def model_to_row(model: BaseModel) -> list[Any]:
    """Convert Pydantic model to list of values for database insertion.

    Args:
        model: Pydantic model instance

    Returns:
        List of values in field order
    """
    return list(model.model_dump().values())
