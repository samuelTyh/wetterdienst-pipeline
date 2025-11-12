"""Prefect flow for weather station ingestion."""

from prefect import flow, task

from src.config import settings
from src.database import operations
from src.ingestion.weather_stations import (
    fetch_stations_by_postal_codes,
    get_ingested_stations,
    parse_stations,
)


@task(name="fetch-postal-codes-for-stations")
def fetch_postal_codes_task(prefix: str | None = None):
    """Fetch postal codes from database."""
    df = operations.get_postal_codes(prefix=prefix)
    return df


@task(name="fetch-weather-stations", retries=3, retry_delay_seconds=10)
def fetch_stations_task(postal_codes_df, max_distance: int = 10000):
    """Fetch weather stations from BrightSky API."""
    return fetch_stations_by_postal_codes(postal_codes_df, max_distance)


@task(name="parse-weather-stations")
def parse_stations_task(stations):
    """Parse station data into DataFrame."""
    return parse_stations(stations)


@task(name="insert-weather-stations")
def insert_stations_task(df):
    """Insert weather stations into database."""
    if df.empty:
        return 0
    operations.insert_weather_stations_df(df)
    return len(df)


@task(name="verify-weather-stations")
def verify_stations_task(expected_count: int, prefix: str | None = None):
    """Verify weather stations were inserted correctly."""
    df = get_ingested_stations(postal_code_prefix=prefix)
    actual_count = len(df)

    if actual_count < expected_count:
        raise ValueError(f"Expected at least {expected_count} stations, but found {actual_count}")

    return actual_count


@flow(name="ingest-weather-stations", log_prints=True)
def ingest_weather_stations_flow(
    prefix: str | None = None,
    max_distance: int = 10000,
):
    """
    Ingest weather stations from BrightSky API for postal code regions.

    This flow fetches weather stations near postal code centroids and stores
    their metadata for use in observations and forecasts ingestion.

    Args:
        prefix: Optional postal code prefix to filter (e.g., "10" for Berlin)
        max_distance: Maximum distance in meters from postal code centroids (default: 50km)

    Returns:
        Number of stations ingested
    """

    print(f"Starting weather station ingestion (prefix: {prefix or 'all'})")
    print(f"Max distance from postal codes: {max_distance}m")

    # Fetch postal codes
    postal_codes_df = fetch_postal_codes_task(prefix=prefix)

    if postal_codes_df.empty:
        print("No postal codes found - cannot proceed")
        return 0

    print(f"Using {len(postal_codes_df)} postal codes as reference points")

    # Fetch stations from API
    stations = fetch_stations_task(postal_codes_df, max_distance)

    if not stations:
        print("No stations found near postal codes")
        return 0

    print(f"Fetched {len(stations)} unique stations from API")

    # Parse station data
    df = parse_stations_task(stations)

    if df.empty:
        print("No valid station data to ingest")
        return 0

    print(f"Parsed {len(df)} stations successfully")

    # Insert into database
    count = insert_stations_task(df)
    print(f"Inserted {count} stations into database")

    # Verify insertion
    actual_count = verify_stations_task(count, prefix=prefix)
    print(f"Verified {actual_count} stations in database")

    print("✓ Weather station ingestion completed successfully")
    return actual_count


if __name__ == "__main__":
    # Run the flow
    for prefix in settings.postal_code_prefixes:
        result = ingest_weather_stations_flow(prefix=prefix)
        print(f"\nFinal result: {result} stations ingested")
