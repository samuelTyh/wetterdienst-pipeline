"""Prefect flow for weather forecasts ingestion."""

from prefect import flow

from src.ingestion.weather_forecasts import ingest_weather_forecasts


@flow(name="ingest-forecasts", log_prints=True)
def ingest_forecasts_flow(prefix: str | None = None, days_ahead: int = 7) -> int:
    """Ingest weather forecasts for a postal code prefix.

    Args:
        prefix: Postal code prefix to filter stations
        days_ahead: Number of days ahead to fetch forecasts

    Returns:
        Number of forecasts ingested
    """
    return ingest_weather_forecasts(postal_code_prefix=prefix, days_ahead=days_ahead)


if __name__ == "__main__":
    # Test run
    count = ingest_forecasts_flow(prefix="10", days_ahead=7)
    print(f"Ingested {count} forecasts")
