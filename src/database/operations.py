"""High-level database operations for weather data pipeline."""

from typing import Any

import pandas as pd

from src.database.clickhouse_client import get_client
from src.database.schema import (
    ForecastByPostalCode,
    ObservationByPostalCode,
    PostalCode,
    WeatherForecast,
    WeatherObservation,
    WeatherObservationSynop,
    WeatherStation,
    model_to_dict,
)


def insert_postal_codes(postal_codes: list[PostalCode]) -> None:
    """Insert postal codes into raw.postal_codes table.

    Args:
        postal_codes: List of postal code models
    """
    client = get_client()
    data = [list(model_to_dict(pc).values()) for pc in postal_codes]
    client.insert("raw.postal_codes", data)


def insert_postal_codes_df(df: pd.DataFrame) -> None:
    """Insert postal codes from DataFrame.

    Args:
        df: DataFrame with postal code data
    """
    client = get_client()
    client.insert_df("raw.postal_codes", df)


def insert_weather_stations(stations: list[WeatherStation]) -> None:
    """Insert weather stations into raw.weather_stations table.

    Args:
        stations: List of weather station models
    """
    client = get_client()
    data = [list(model_to_dict(s).values()) for s in stations]
    client.insert("raw.weather_stations", data)


def insert_weather_stations_df(df: pd.DataFrame) -> None:
    """Insert weather stations from DataFrame.

    Args:
        df: DataFrame with station data
    """
    client = get_client()
    client.insert_df("raw.weather_stations", df)


def insert_weather_observations_synop(observations: list[WeatherObservationSynop]) -> None:
    """Insert SYNOP weather observations into raw.weather_observations_synop table.

    Args:
        observations: List of SYNOP observation models
    """
    client = get_client()
    data = [list(model_to_dict(obs).values()) for obs in observations]
    client.insert("raw.weather_observations_synop", data)


def insert_weather_observations_synop_df(df: pd.DataFrame) -> None:
    """Insert SYNOP weather observations from DataFrame.

    Args:
        df: DataFrame with SYNOP observation data
    """
    client = get_client()
    client.insert_df("raw.weather_observations_synop", df)


def insert_weather_observations(observations: list[WeatherObservation]) -> None:
    """Insert weather observations into raw.weather_observations table.

    Args:
        observations: List of observation models
    """
    client = get_client()
    data = [list(model_to_dict(obs).values()) for obs in observations]
    client.insert("raw.weather_observations", data)


def insert_weather_observations_df(df: pd.DataFrame) -> None:
    """Insert weather observations from DataFrame.

    Args:
        df: DataFrame with observation data
    """
    client = get_client()
    client.insert_df("raw.weather_observations", df)


def insert_weather_forecasts(forecasts: list[WeatherForecast]) -> None:
    """Insert weather forecasts into raw.weather_forecasts table.

    Args:
        forecasts: List of forecast models
    """
    client = get_client()
    data = [list(model_to_dict(fc).values()) for fc in forecasts]
    client.insert("raw.weather_forecasts", data)


def insert_weather_forecasts_df(df: pd.DataFrame) -> None:
    """Insert weather forecasts from DataFrame.

    Args:
        df: DataFrame with forecast data
    """
    client = get_client()
    client.insert_df("raw.weather_forecasts", df)


def insert_observations_by_postal_code(observations: list[ObservationByPostalCode]) -> None:
    """Insert cleaned observations into staging.observations_by_postal_code table.

    Args:
        observations: List of observation models
    """
    client = get_client()
    data = [list(model_to_dict(obs).values()) for obs in observations]
    client.insert("staging.observations_by_postal_code", data)


def insert_observations_by_postal_code_df(df: pd.DataFrame) -> None:
    """Insert cleaned observations from DataFrame.

    Args:
        df: DataFrame with observation data
    """
    client = get_client()
    client.insert_df("staging.observations_by_postal_code", df)


def insert_forecasts_by_postal_code(forecasts: list[ForecastByPostalCode]) -> None:
    """Insert cleaned forecasts into staging.forecasts_by_postal_code table.

    Args:
        forecasts: List of forecast models
    """
    client = get_client()
    data = [list(model_to_dict(fc).values()) for fc in forecasts]
    client.insert("staging.forecasts_by_postal_code", data)


def insert_forecasts_by_postal_code_df(df: pd.DataFrame) -> None:
    """Insert cleaned forecasts from DataFrame.

    Args:
        df: DataFrame with forecast data
    """
    client = get_client()
    client.insert_df("staging.forecasts_by_postal_code", df)


def get_postal_codes(prefix: str | None = None) -> pd.DataFrame:
    """Get postal codes, optionally filtered by prefix.

    Args:
        prefix: Optional postal code prefix to filter (e.g., "10" for Berlin)

    Returns:
        DataFrame with postal code data
    """
    client = get_client()
    if prefix:
        query = f"SELECT * FROM raw.postal_codes WHERE plz LIKE '{prefix}%' ORDER BY plz"
    else:
        query = "SELECT * FROM raw.postal_codes ORDER BY plz"
    return client.query_df(query)


def get_weather_stations(
    observation_type: str | None = None,
    postal_code_prefix: str | None = None,
) -> pd.DataFrame:
    """Get weather stations, optionally filtered.

    Args:
        observation_type: Optional filter by observation type
        postal_code_prefix: Optional postal code prefix for spatial filtering

    Returns:
        DataFrame with station data
    """
    client = get_client()
    query = "SELECT * FROM raw.weather_stations WHERE 1=1"

    if observation_type:
        query += f" AND observation_type = '{observation_type}'"

    query += " ORDER BY id"
    return client.query_df(query)


def get_latest_observations_synop(
    source_id: int | None = None,
    limit: int = 100,
) -> pd.DataFrame:
    """Get latest SYNOP weather observations.

    Args:
        source_id: Optional filter by source ID
        limit: Maximum number of records to return

    Returns:
        DataFrame with SYNOP observation data
    """
    client = get_client()
    query = "SELECT * FROM raw.weather_observations_synop WHERE 1=1"

    if source_id:
        query += f" AND source_id = {source_id}"

    query += f" ORDER BY timestamp DESC LIMIT {limit}"
    return client.query_df(query)


def get_latest_observations(
    source_id: int | None = None,
    limit: int = 100,
) -> pd.DataFrame:
    """Get latest weather observations.

    Args:
        source_id: Optional filter by source ID
        limit: Maximum number of records to return

    Returns:
        DataFrame with observation data
    """
    client = get_client()
    query = "SELECT * FROM raw.weather_observations WHERE 1=1"

    if source_id:
        query += f" AND source_id = {source_id}"

    query += f" ORDER BY timestamp DESC LIMIT {limit}"
    return client.query_df(query)


def get_latest_forecasts(
    source_id: int | None = None,
    limit: int = 100,
) -> pd.DataFrame:
    """Get latest weather forecasts.

    Args:
        source_id: Optional filter by source ID
        limit: Maximum number of records to return

    Returns:
        DataFrame with forecast data
    """
    client = get_client()
    query = "SELECT * FROM raw.weather_forecasts WHERE 1=1"

    if source_id:
        query += f" AND source_id = {source_id}"

    query += f" ORDER BY forecast_created_at DESC, timestamp DESC LIMIT {limit}"
    return client.query_df(query)


def get_table_counts() -> dict[str, int]:
    """Get row counts for all tables.

    Returns:
        Dictionary mapping table names to row counts
    """
    client = get_client()
    tables = {
        "raw.postal_codes": "raw.postal_codes",
        "raw.weather_stations": "raw.weather_stations",
        "raw.weather_observations_synop": "raw.weather_observations_synop",
        "raw.weather_observations": "raw.weather_observations",
        "raw.weather_forecasts": "raw.weather_forecasts",
        "staging.observations_by_postal_code": "staging.observations_by_postal_code",
        "staging.forecasts_by_postal_code": "staging.forecasts_by_postal_code",
    }

    counts = {}
    for name, table in tables.items():
        try:
            result = client.execute(f"SELECT count() FROM {table}")
            counts[name] = result.result_rows[0][0] if result.result_rows else 0
        except Exception:
            counts[name] = 0

    return counts


def get_database_status() -> dict[str, Any]:
    """Get overall database status and statistics.

    Returns:
        Dictionary with database statistics
    """
    client = get_client()
    counts = get_table_counts()

    # Get latest ingestion timestamps
    latest_timestamps = {}
    for table in [
        "postal_codes",
        "weather_stations",
        "weather_observations_synop",
        "weather_observations",
        "weather_forecasts",
    ]:
        try:
            query = f"SELECT max(ingested_at) FROM raw.{table}"
            result = client.execute(query)
            if result.result_rows and result.result_rows[0][0]:
                latest_timestamps[table] = result.result_rows[0][0]
        except Exception:
            pass

    # Get date range for SYNOP observations
    try:
        synop_range = client.execute(
            "SELECT min(timestamp), max(timestamp) FROM raw.weather_observations_synop"
        )
        if synop_range.result_rows and synop_range.result_rows[0][0]:
            counts["synop_observation_date_range"] = synop_range.result_rows[0]
    except Exception:
        pass

    # Get date range for observations
    try:
        obs_range = client.execute(
            "SELECT min(timestamp), max(timestamp) FROM raw.weather_observations"
        )
        if obs_range.result_rows and obs_range.result_rows[0][0]:
            counts["observation_date_range"] = obs_range.result_rows[0]
    except Exception:
        pass

    # Get date range for forecasts
    try:
        fc_range = client.execute(
            "SELECT min(timestamp), max(timestamp) FROM raw.weather_forecasts"
        )
        if fc_range.result_rows and fc_range.result_rows[0][0]:
            counts["forecast_date_range"] = fc_range.result_rows[0]
    except Exception:
        pass

    return {
        "table_counts": counts,
        "latest_ingestions": latest_timestamps,
    }


def test_connection() -> bool:
    """Test database connection.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        client = get_client()
        result = client.execute("SELECT 1")
        return result.result_rows[0][0] == 1
    except Exception:
        return False
