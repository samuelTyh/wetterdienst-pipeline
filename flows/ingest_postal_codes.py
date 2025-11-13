"""(Deprecated)Prefect flow for postal code ingestion."""

from prefect import flow, task

from src.config import settings
from src.database import operations
from src.ingestion.postal_codes import (
    fetch_postal_codes_geojson,
    get_ingested_postal_codes,
    parse_postal_codes,
)


@task(name="fetch-postal-codes", retries=3, retry_delay_seconds=10)
def fetch_postal_codes_task():
    """Fetch postal code GeoJSON from GitHub."""
    return fetch_postal_codes_geojson()


@task(name="parse-postal-codes")
def parse_postal_codes_task(geojson_data, prefix: str | None = None):
    """Parse GeoJSON data into DataFrame."""
    return parse_postal_codes(geojson_data, prefix=prefix)


@task(name="insert-postal-codes")
def insert_postal_codes_task(df):
    """Insert postal codes into database."""
    operations.insert_postal_codes_df(df)
    return len(df)


@task(name="verify-postal-codes")
def verify_postal_codes_task(expected_count: int, prefix: str | None = None):
    """Verify postal codes were inserted correctly."""
    df = get_ingested_postal_codes(prefix=prefix)
    actual_count = len(df)

    if actual_count < expected_count:
        raise ValueError(
            f"Expected at least {expected_count} postal codes, but found {actual_count}"
        )

    return actual_count


@flow(name="ingest-postal-codes", log_prints=True)
def ingest_postal_codes_flow(prefix: str | None = None):
    """
    Ingest German postal codes from GitHub repository.

    This is typically a one-time operation that loads postal code geometries
    and centroids for spatial operations.

    Args:
        prefix: Optional postal code prefix to filter (e.g., "10" for Berlin)

    Returns:
        Number of postal codes ingested
    """

    print(f"Starting postal code ingestion (prefix: {prefix or 'all'})")

    # Fetch data from GitHub
    geojson_data = fetch_postal_codes_task()
    print(f"Fetched GeoJSON data with {len(geojson_data.get('features', []))} features")

    # Parse and filter data
    df = parse_postal_codes_task(geojson_data, prefix=prefix)
    print(f"Parsed {len(df)} postal codes")

    # Insert into database
    count = insert_postal_codes_task(df)
    print(f"Inserted {count} postal codes into database")

    # Verify insertion
    actual_count = verify_postal_codes_task(count, prefix=prefix)
    print(f"Verified {actual_count} postal codes in database")

    print("✓ Postal code ingestion completed successfully")
    return actual_count


if __name__ == "__main__":
    # Run the flow
    result = ingest_postal_codes_flow()
    print(f"\nFinal result: {result} postal codes ingested")
