"""Prefect flow for forecast transformation."""

from prefect import flow

from src.transformation.forecast_transformer import ForecastTransformer


@flow(name="transform-forecasts", log_prints=True)
def transform_forecasts_flow(prefix: str | None = None, days_ahead: int = 7) -> int:
    """Transform forecasts to postal code level.

    Args:
        prefix: Postal code prefix to filter
        days_ahead: Number of days ahead to transform

    Returns:
        Number of forecasts transformed
    """
    transformer = ForecastTransformer(max_distance_km=10.0, min_stations=1)
    return transformer.transform(prefix=prefix, days_ahead=days_ahead)


if __name__ == "__main__":
    # Test run
    count = transform_forecasts_flow(prefix="10", days_ahead=7)
    print(f"Transformed {count} forecasts")
