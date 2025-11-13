"""Prefect flow for observation transformation."""

from prefect import flow

from src.transformation.observation_transformer import ObservationTransformer


@flow(name="transform-observations", log_prints=True)
def transform_observations_flow(prefix: str | None = None, hours_back: int = 24) -> int:
    """Transform SYNOP observations to postal code level.

    Args:
        prefix: Postal code prefix to filter
        hours_back: Number of hours back to transform

    Returns:
        Number of observations transformed
    """
    transformer = ObservationTransformer(max_distance_km=10.0, min_stations=1)
    return transformer.transform(prefix=prefix, hours_back=hours_back)


if __name__ == "__main__":
    # Test run
    count = transform_observations_flow(prefix="10", hours_back=24)
    print(f"Transformed {count} observations")
