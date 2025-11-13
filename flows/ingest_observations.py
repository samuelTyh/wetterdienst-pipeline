"""Prefect flow for weather observations ingestion.

Uses /current_weather endpoint with SYNOP stations for high-quality current weather data.
"""

from prefect import flow, task

from src.config import settings
from src.database import operations
from src.ingestion.weather_observations import (
    fetch_current_weather_for_stations,
    get_active_synop_stations,
    get_ingested_observations,
    parse_observations,
)


@task(name="fetch-active-synop-stations")
def fetch_stations_task(prefix: str | None = None):
    """Fetch active SYNOP stations from database."""
    return get_active_synop_stations(postal_code_prefix=prefix)


@task(name="fetch-current-weather", retries=3, retry_delay_seconds=10)
def fetch_observations_task(stations_df):
    """Fetch current weather from BrightSky API."""
    return fetch_current_weather_for_stations(stations_df)


@task(name="parse-current-weather")
def parse_observations_task(observations):
    """Parse observation data into DataFrame."""
    return parse_observations(observations)


@task(name="insert-synop-observations")
def insert_observations_task(df):
    """Insert SYNOP weather observations into database."""
    if df.empty:
        return 0
    operations.insert_weather_observations_synop_df(df)
    return len(df)


@task(name="verify-current-weather")
def verify_observations_task(expected_count: int, source_id: int | None = None):
    """Verify weather observations were inserted correctly."""
    df = get_ingested_observations(source_id=source_id, limit=expected_count + 100)
    actual_count = len(df)

    if actual_count < expected_count:
        print(
            f"⚠ Warning: Expected at least {expected_count} observations, but found {actual_count}"
        )
        # Don't fail - observations may have been deduplicated

    return actual_count


@flow(name="ingest-current-weather-observations", log_prints=True)
def ingest_weather_observations_flow(prefix: str | None = None):
    """
    Ingest current weather observations from BrightSky API using SYNOP stations.

    This flow fetches the most recent weather observations using the /current_weather
    endpoint, which provides high-quality SYNOP data with 10-minute resolution.
    The API automatically returns the most recent observation for each station.

    Key features:
    - Uses SYNOP stations (observation_type='synop')
    - Filters to active stations (last_record >= today)
    - Fetches current weather (no date parameters needed)
    - 10-minute temporal resolution
    - Scheduled to run hourly (DWD updates twice per hour)

    Args:
        prefix: Optional postal code prefix to filter stations (e.g., "10" for Berlin)

    Returns:
        Number of observations ingested
    """
    print(f"Starting current weather observations ingestion (prefix: {prefix or 'all'})")
    print("Using /current_weather endpoint with SYNOP stations")

    # Fetch active SYNOP stations
    stations_df = fetch_stations_task(prefix=prefix)

    if stations_df.empty:
        print("No active SYNOP stations found")
        print("Note: Stations must have observation_type='synop' and last_record >= today")
        return 0

    print(f"Using {len(stations_df)} active SYNOP stations")

    # Fetch current weather from API
    observations = fetch_observations_task(stations_df)

    if not observations:
        print("No current weather data found from API")
        return 0

    print(f"Fetched {len(observations)} current weather records from API")

    # Parse observation data
    df = parse_observations_task(observations)

    if df.empty:
        print("No valid observation data to ingest")
        return 0

    print(f"Parsed {len(df)} unique observations successfully")

    # Insert into database
    count = insert_observations_task(df)
    print(f"Inserted {count} observations into database")

    # Verify insertion
    actual_count = verify_observations_task(count)
    print(f"Verified {actual_count} observations in database")

    print("✓ Current weather observations ingestion completed successfully")
    return count


if __name__ == "__main__":
    # Run the flow for all configured prefixes
    total_count = 0
    for prefix in settings.postal_code_prefixes:
        print(f"\n{'=' * 60}")
        print(f"Processing prefix: {prefix}")
        print(f"{'=' * 60}")

        result = ingest_weather_observations_flow(prefix=prefix)
        total_count += result
        print(f"Result: {result} observations ingested for prefix {prefix}")

    print(f"\n{'=' * 60}")
    print(f"Total: {total_count} observations ingested across all prefixes")
    print(f"{'=' * 60}")
