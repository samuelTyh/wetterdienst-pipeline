"""Weather station data ingestion from BrightSky API."""

from datetime import datetime
from typing import Any

import httpx
import pandas as pd

from src.config import settings
from src.database import operations


def fetch_stations_by_location(
    lat: float,
    lon: float,
    max_distance: int = 10000,  # 10km default
    timeout: float = 30.0,
) -> list[dict[str, Any]]:
    """Fetch weather stations near a location from BrightSky API.

    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        max_distance: Maximum distance in meters (default: 50km)
        timeout: HTTP timeout in seconds

    Returns:
        List of station dictionaries from API

    Raises:
        httpx.HTTPError: If request fails
    """
    url = f"{settings.brightsky_base_url}/sources"
    params = {"lat": lat, "lon": lon, "max_dist": max_distance}

    response = httpx.get(url, params=params, timeout=timeout, follow_redirects=True)
    response.raise_for_status()

    data = response.json()
    sources = data.get("sources", [])

    print(f"Fetched {len(sources)} stations near ({lat}, {lon})")
    return sources


def fetch_stations_by_postal_codes(
    postal_codes_df: pd.DataFrame,
    max_distance: int = 10000,
) -> list[dict[str, Any]]:
    """Fetch weather stations for multiple postal codes.

    Args:
        postal_codes_df: DataFrame with columns: plz, centroid_lat, centroid_lon
        max_distance: Maximum distance in meters from each centroid

    Returns:
        List of unique station dictionaries
    """
    all_stations = []
    seen_station_ids = set()

    print(f"Fetching stations for {len(postal_codes_df)} postal codes...")

    for idx, row in postal_codes_df.iterrows():
        plz = row["plz"]
        lat = row["centroid_lat"]
        lon = row["centroid_lon"]

        try:
            stations = fetch_stations_by_location(lat, lon, max_distance)

            # Deduplicate by station id
            for station in stations:
                station_id = station["id"]
                if station_id not in seen_station_ids:
                    all_stations.append(station)
                    seen_station_ids.add(station_id)

            print(f"  PLZ {plz}: Found {len(stations)} stations, {len(all_stations)} unique total")

        except Exception as e:
            print(f"  PLZ {plz}: Error fetching stations: {e}")
            continue

    print(f"Total unique stations fetched: {len(all_stations)}")
    return all_stations


def parse_stations(stations: list[dict[str, Any]]) -> pd.DataFrame:
    """Parse station data into DataFrame.

    Args:
        stations: List of station dictionaries from API

    Returns:
        DataFrame with station data
    """
    if not stations:
        return pd.DataFrame()

    # Convert to DataFrame
    df = pd.DataFrame(stations)

    # Parse datetime fields
    if "first_record" in df.columns:
        df["first_record"] = pd.to_datetime(df["first_record"], utc=True)

    if "last_record" in df.columns:
        df["last_record"] = pd.to_datetime(df["last_record"], utc=True)

    # Ensure required columns exist
    required_columns = [
        "id",
        "dwd_station_id",
        "wmo_station_id",
        "station_name",
        "observation_type",
        "lat",
        "lon",
        "height",
        "first_record",
        "last_record",
    ]

    # Add missing columns with None
    for col in required_columns:
        if col not in df.columns:
            df[col] = None

    # Handle optional distance field
    if "distance" not in df.columns:
        df["distance"] = None

    # Select and order columns to match database schema
    df = df[required_columns + ["distance"]]

    print(f"Parsed {len(df)} stations")
    print(f"  Observation types: {df['observation_type'].value_counts().to_dict()}")

    return df


def ingest_weather_stations(
    postal_code_prefix: str | None = None,
    max_distance: int = 10000,
) -> int:
    """Ingest weather stations for postal codes.

    Args:
        postal_code_prefix: Optional postal code prefix to filter
        max_distance: Maximum distance in meters from postal code centroids

    Returns:
        Number of stations ingested
    """
    # Get postal codes
    print(f"Fetching postal codes (prefix: {postal_code_prefix or 'all'})...")
    postal_codes_df = operations.get_postal_codes(prefix=postal_code_prefix)

    if postal_codes_df.empty:
        print("No postal codes found")
        return 0

    print(f"Found {len(postal_codes_df)} postal codes")

    # Fetch stations
    stations = fetch_stations_by_postal_codes(postal_codes_df, max_distance)

    if not stations:
        print("No stations found")
        return 0

    # Parse data
    print("Parsing station data...")
    df = parse_stations(stations)

    if df.empty:
        print("No valid station data to ingest")
        return 0

    # Insert into database
    print(f"Inserting {len(df)} stations into database...")
    operations.insert_weather_stations_df(df)

    print(f"✓ Successfully ingested {len(df)} weather stations")
    return len(df)


def get_ingested_stations(
    observation_type: str | None = None,
    postal_code_prefix: str | None = None,
) -> pd.DataFrame:
    """Get weather stations from database.

    Args:
        observation_type: Optional filter by observation type
        postal_code_prefix: Optional postal code prefix for spatial filtering

    Returns:
        DataFrame with station data
    """
    return operations.get_weather_stations(
        observation_type=observation_type,
        postal_code_prefix=postal_code_prefix,
    )


if __name__ == "__main__":
    # Run ingestion with configured prefix
    for prefix in settings.postal_code_prefixes:
        count = ingest_weather_stations(postal_code_prefix=prefix)
        print(f"\nIngested {count} weather stations")

        df = get_ingested_stations(postal_code_prefix=prefix)
        print(f"\nSample of {len(df)} stations:")
        print(df.head())

        # Show observation types
        if not df.empty:
            print("\nObservation types:")
            print(df["observation_type"].value_counts())
