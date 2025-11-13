"""Weather forecasts data ingestion from BrightSky API.

This module uses the /weather endpoint with forecast-type stations for
7-day weather forecasts.
"""

from datetime import datetime, timedelta
from typing import Any

import httpx
import pandas as pd

from src.config import settings
from src.database import operations


def get_forecast_stations(postal_code_prefix: str | None = None) -> pd.DataFrame:
    """Get forecast-type stations.

    Args:
        postal_code_prefix: Optional postal code prefix to filter stations

    Returns:
        DataFrame with forecast stations
    """
    stations = operations.get_weather_stations(
        observation_type="forecast", postal_code_prefix=postal_code_prefix
    )
    # Filter to stations with furthest data (last_record >= 8 days ahead)
    threshold_date = datetime.now() + timedelta(days=8)

    if not stations.empty and "last_record" in stations.columns:
        stations_filtered = stations[stations["last_record"] >= threshold_date]
    else:
        stations_filtered = pd.DataFrame(columns=stations.columns)

    print(f"Found {len(stations_filtered)} forecast stations")

    return stations_filtered


def fetch_forecasts_by_station(
    source_id: int,
    days_ahead: int = 7,
    timeout: float = 30.0,
) -> tuple[list[dict[str, Any]], datetime]:
    """Fetch weather forecasts for a station using /weather endpoint.

    Args:
        source_id: Station source ID
        days_ahead: Number of days ahead to fetch forecasts
        timeout: HTTP timeout in seconds

    Returns:
        Tuple of (forecast list, forecast_created_at timestamp)

    Raises:
        httpx.HTTPError: If request fails
    """
    url = f"{settings.brightsky_base_url}/weather"

    # Date range: today to days_ahead
    today = datetime.now().date()
    end_date = today + timedelta(days=days_ahead)

    params = {
        "source_id": source_id,
        "date": today.isoformat(),
        "last_date": end_date.isoformat(),
    }

    response = httpx.get(url, params=params, timeout=timeout, follow_redirects=True)
    response.raise_for_status()

    data = response.json()
    weather = data.get("weather", [])
    sources = data.get("sources", [])

    # Extract forecast_created_at from sources
    forecast_created_at = datetime.now()
    if sources and len(sources) > 0:
        first_record = sources[0].get("first_record")
        if first_record:
            forecast_created_at = pd.to_datetime(first_record, utc=True).to_pydatetime()

    if weather:
        print(f"  Station {source_id}: Got {len(weather)} forecast records")
    else:
        print(f"  Station {source_id}: No forecast data")

    return weather, forecast_created_at


def fetch_forecasts_for_stations(
    stations_df: pd.DataFrame,
    days_ahead: int = 7,
) -> list[dict[str, Any]]:
    """Fetch forecasts for multiple stations.

    Args:
        stations_df: DataFrame with column: id (source_id)
        days_ahead: Number of days ahead to fetch

    Returns:
        List of forecast dictionaries with forecast_created_at added
    """
    all_forecasts = []

    if stations_df.empty:
        print("No stations to fetch")
        return []

    print(f"Fetching {days_ahead}-day forecasts for {len(stations_df)} stations...")

    for idx, row in stations_df.iterrows():
        source_id = row["id"]
        station_name = row.get("station_name", "Unknown")

        try:
            forecasts, forecast_created_at = fetch_forecasts_by_station(
                source_id, days_ahead=days_ahead
            )

            # Add forecast_created_at to each forecast
            for forecast in forecasts:
                forecast["forecast_created_at"] = forecast_created_at
                all_forecasts.append(forecast)

            if forecasts:
                print(
                    f"  Station {source_id} ({station_name}): "
                    f"{len(forecasts)} records, created_at={forecast_created_at}"
                )

        except Exception as e:
            print(f"  Station {source_id} ({station_name}): Error: {e}")
            continue

    print(f"Total forecast records fetched: {len(all_forecasts)}")
    return all_forecasts


def parse_forecasts(forecasts: list[dict[str, Any]]) -> pd.DataFrame:
    """Parse forecast data into DataFrame.

    Args:
        forecasts: List of forecast dictionaries from API

    Returns:
        DataFrame with forecast data
    """
    if not forecasts:
        return pd.DataFrame()

    df = pd.DataFrame(forecasts)

    # Parse timestamp fields
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    if "forecast_created_at" in df.columns:
        df["forecast_created_at"] = pd.to_datetime(df["forecast_created_at"], utc=True)

    # Required columns for forecasts
    required_columns = [
        "source_id",
        "timestamp",
        "cloud_cover",
        "condition",
        "dew_point",
        "icon",
        "precipitation",
        "precipitation_probability",
        "precipitation_probability_6h",
        "pressure_msl",
        "relative_humidity",
        "sunshine",
        "temperature",
        "visibility",
        "wind_direction",
        "wind_speed",
        "wind_gust_direction",
        "wind_gust_speed",
        "forecast_created_at",
    ]

    # Add missing columns with None
    for col in required_columns:
        if col not in df.columns:
            df[col] = None

    # Select and order columns
    df = df[required_columns]

    # Remove duplicates
    df = df.drop_duplicates(subset=["source_id", "timestamp", "forecast_created_at"])

    print(f"Parsed {len(df)} unique forecast records")
    if not df.empty:
        print(f"  Timestamp range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"  Unique stations: {df['source_id'].nunique()}")
        print(f"  Forecast created at: {df['forecast_created_at'].iloc[0]}")

    return df


def ingest_weather_forecasts(
    postal_code_prefix: str | None = None,
    days_ahead: int = 7,
) -> int:
    """Ingest weather forecasts for forecast-type stations.

    Args:
        postal_code_prefix: Optional postal code prefix to filter stations
        days_ahead: Number of days ahead to fetch forecasts

    Returns:
        Number of forecasts ingested
    """
    print(
        f"Fetching weather forecasts (prefix: {postal_code_prefix or 'all'}, days: {days_ahead})..."
    )

    # Get forecast stations
    stations_df = get_forecast_stations(postal_code_prefix=postal_code_prefix)

    if stations_df.empty:
        print("No forecast stations found")
        return 0

    # Fetch forecasts
    forecasts = fetch_forecasts_for_stations(stations_df, days_ahead=days_ahead)

    if not forecasts:
        print("No forecast data found")
        return 0

    # Parse data
    print("Parsing forecast data...")
    df = parse_forecasts(forecasts)

    if df.empty:
        print("No valid forecast data to ingest")
        return 0

    # Insert into database
    print(f"Inserting {len(df)} forecasts into database...")
    operations.insert_weather_forecasts_df(df)

    print(f"✓ Successfully ingested {len(df)} weather forecasts")
    return len(df)


def get_ingested_forecasts(
    source_id: int | None = None,
    limit: int = 100,
) -> pd.DataFrame:
    """Get weather forecasts from database.

    Args:
        source_id: Optional filter by source ID
        limit: Maximum number of records to return

    Returns:
        DataFrame with forecast data
    """
    return operations.get_latest_forecasts(source_id=source_id, limit=limit)


if __name__ == "__main__":
    # Run ingestion for forecasts
    total_count = 0
    for prefix in settings.postal_code_prefixes:
        print(f"\n{'=' * 60}")
        print(f"Processing prefix: {prefix}")
        print(f"{'=' * 60}")

        count = ingest_weather_forecasts(postal_code_prefix=prefix, days_ahead=7)
        total_count += count
        print(f"Ingested {count} forecasts for prefix {prefix}")

    print(f"\n{'=' * 60}")
    print(f"Total ingested: {total_count} weather forecasts")
    print(f"{'=' * 60}")

    # Show sample
    df = get_ingested_forecasts(limit=10)
    if not df.empty:
        print("\nSample forecasts:")
        print(df[["source_id", "timestamp", "temperature", "precipitation", "condition"]].head())
