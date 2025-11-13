"""Weather observations data ingestion from BrightSky API.

This module uses the /current_weather endpoint with SYNOP stations for
high-quality, current weather data with 10-minute resolution.
"""

from datetime import datetime
from typing import Any

import httpx
import pandas as pd

from src.config import settings
from src.database import operations


def get_active_synop_stations(postal_code_prefix: str | None = None) -> pd.DataFrame:
    """Get active SYNOP stations with recent data.

    Args:
        postal_code_prefix: Optional postal code prefix to filter stations

    Returns:
        DataFrame with active SYNOP stations that have data from today
    """
    # Get SYNOP-type stations
    stations = operations.get_weather_stations(
        observation_type="synop", postal_code_prefix=postal_code_prefix
    )

    if stations.empty:
        return stations

    # Filter to stations with recent data (last_record >= today)
    today = datetime.now().date()
    stations["last_record_date"] = pd.to_datetime(stations["last_record"]).dt.date

    active_stations = stations[stations["last_record_date"] >= today].copy()

    print(
        f"Filtered {len(stations)} SYNOP stations → "
        f"{len(active_stations)} active stations (last_record >= today)"
    )

    return active_stations.drop(columns=["last_record_date"])


def fetch_current_weather_by_station(
    source_id: int,
    timeout: float = 30.0,
) -> dict[str, Any] | None:
    """Fetch current weather for a station using /current_weather endpoint.

    Args:
        source_id: Station source ID
        timeout: HTTP timeout in seconds

    Returns:
        Weather data dictionary or None if no data available

    Raises:
        httpx.HTTPError: If request fails
    """
    url = f"{settings.brightsky_base_url}/current_weather"
    params = {"source_id": source_id}

    response = httpx.get(url, params=params, timeout=timeout, follow_redirects=True)
    response.raise_for_status()

    data = response.json()
    weather = data.get("weather", {})

    if weather:
        print(f"  Station {source_id}: Got current weather")
        return weather
    else:
        print(f"  Station {source_id}: No current weather data")
        return None


def fetch_current_weather_for_stations(
    stations_df: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Fetch current weather for multiple SYNOP stations.

    Args:
        stations_df: DataFrame with column: id (source_id)

    Returns:
        List of current weather dictionaries
    """
    all_observations = []

    if stations_df.empty:
        print("No stations to fetch")
        return []

    print(f"Fetching current weather for {len(stations_df)} SYNOP stations...")

    for idx, row in stations_df.iterrows():
        source_id = row["id"]
        station_name = row.get("station_name", "Unknown")

        try:
            weather = fetch_current_weather_by_station(source_id)

            if weather:
                all_observations.append(weather)
                print(
                    f"  Station {source_id} ({station_name}): "
                    f"temp={weather.get('temperature')}°C, "
                    f"time={weather.get('timestamp')}"
                )
            else:
                print(f"  Station {source_id} ({station_name}): No data")

        except Exception as e:
            print(f"  Station {source_id} ({station_name}): Error: {e}")
            continue

    print(f"Total current weather records fetched: {len(all_observations)}")
    return all_observations


def parse_observations(observations: list[dict[str, Any]]) -> pd.DataFrame:
    """Parse observation data into DataFrame.

    Args:
        observations: List of observation dictionaries from API

    Returns:
        DataFrame with observation data
    """
    if not observations:
        return pd.DataFrame()

    # Convert to DataFrame
    df = pd.DataFrame(observations)

    # Parse timestamp field
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    # Ensure required columns exist (SYNOP-specific fields)
    required_columns = [
        "source_id",
        "timestamp",
        "cloud_cover",
        "condition",
        "dew_point",
        "icon",
        "pressure_msl",
        "relative_humidity",
        "temperature",
        "visibility",
        "precipitation_10",
        "precipitation_30",
        "precipitation_60",
        "solar_10",
        "solar_30",
        "solar_60",
        "sunshine_30",
        "sunshine_60",
        "wind_direction_10",
        "wind_direction_30",
        "wind_direction_60",
        "wind_speed_10",
        "wind_speed_30",
        "wind_speed_60",
        "wind_gust_direction_10",
        "wind_gust_direction_30",
        "wind_gust_direction_60",
        "wind_gust_speed_10",
        "wind_gust_speed_30",
        "wind_gust_speed_60",
    ]

    # Add missing columns with None
    for col in required_columns:
        if col not in df.columns:
            df[col] = None

    # Select and order columns to match database schema
    df = df[required_columns]

    # Remove duplicates (by source_id and timestamp)
    df = df.drop_duplicates(subset=["source_id", "timestamp"])

    print(f"Parsed {len(df)} unique SYNOP observations")
    if not df.empty:
        print(f"  Timestamp range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"  Unique stations: {df['source_id'].nunique()}")

    return df


def ingest_weather_observations(
    postal_code_prefix: str | None = None,
) -> int:
    """Ingest current weather observations for SYNOP stations.

    This function fetches current weather data using the /current_weather endpoint
    which returns the most recent SYNOP observation for each station.

    Args:
        postal_code_prefix: Optional postal code prefix to filter stations

    Returns:
        Number of observations ingested
    """
    print(f"Fetching current weather observations (prefix: {postal_code_prefix or 'all'})...")

    # Get active SYNOP stations
    print(f"Getting active SYNOP stations (prefix: {postal_code_prefix or 'all'})...")
    stations_df = get_active_synop_stations(postal_code_prefix=postal_code_prefix)

    if stations_df.empty:
        print("No active SYNOP stations found")
        print("Note: Stations must have observation_type='synop' and last_record >= today")
        return 0

    print(f"Found {len(stations_df)} active SYNOP stations")

    # Fetch current weather
    observations = fetch_current_weather_for_stations(stations_df)

    if not observations:
        print("No current weather data found")
        return 0

    # Parse data
    print("Parsing observation data...")
    df = parse_observations(observations)

    if df.empty:
        print("No valid observation data to ingest")
        return 0

    # Insert into database
    print(f"Inserting {len(df)} SYNOP observations into database...")
    operations.insert_weather_observations_synop_df(df)

    print(f"✓ Successfully ingested {len(df)} SYNOP current weather observations")
    return len(df)


def get_ingested_observations(
    source_id: int | None = None,
    limit: int = 100,
) -> pd.DataFrame:
    """Get SYNOP weather observations from database.

    Args:
        source_id: Optional filter by source ID
        limit: Maximum number of records to return

    Returns:
        DataFrame with SYNOP observation data
    """
    return operations.get_latest_observations_synop(source_id=source_id, limit=limit)


if __name__ == "__main__":
    # Run ingestion for current weather
    total_count = 0
    for prefix in settings.postal_code_prefixes:
        print(f"\n{'=' * 60}")
        print(f"Processing prefix: {prefix}")
        print(f"{'=' * 60}")

        count = ingest_weather_observations(postal_code_prefix=prefix)
        total_count += count
        print(f"Ingested {count} observations for prefix {prefix}")

    print(f"\n{'=' * 60}")
    print(f"Total ingested: {total_count} current weather observations")
    print(f"{'=' * 60}")

    # Show sample
    df = get_ingested_observations(limit=10)
    if not df.empty:
        print("\nSample observations:")
        print(df[["source_id", "timestamp", "temperature", "precipitation", "condition"]].head())
