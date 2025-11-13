"""Base transformer for weather data aggregation."""

from abc import ABC, abstractmethod
from datetime import datetime

import pandas as pd

from src.config import settings
from src.database import operations
from src.database.clickhouse_client import get_client
from src.transformation.cleaner import WeatherDataCleaner, get_default_cleaner


class BaseWeatherTransformer(ABC):
    """Base class for weather data transformation to postal code level."""

    def __init__(
        self,
        max_distance_km: float = 10.0,
        min_stations: int = 1,
        cleaner: WeatherDataCleaner | None = None,
    ):
        """Initialize transformer.

        Args:
            max_distance_km: Maximum distance to search for stations
            min_stations: Minimum number of stations required for aggregation
            cleaner: Data cleaner instance (uses default if None)
        """
        self.max_distance_km = max_distance_km
        self.min_stations = min_stations
        self.cleaner = cleaner or get_default_cleaner()
        self.client = get_client()

    def get_postal_codes(self, prefix: str | None = None) -> pd.DataFrame:
        """Get postal codes with centroids.

        Args:
            prefix: Optional postal code prefix filter

        Returns:
            DataFrame with postal codes
        """
        return operations.get_postal_codes(prefix=prefix)

    def calculate_haversine_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points using Haversine formula.

        Args:
            lat1: Latitude of first point
            lon1: Longitude of first point
            lat2: Latitude of second point
            lon2: Longitude of second point

        Returns:
            Distance in kilometers
        """
        query = f"""
        SELECT 6371 * acos(
            cos(radians({lat1})) * cos(radians({lat2})) *
            cos(radians({lon2}) - radians({lon1})) +
            sin(radians({lat1})) * sin(radians({lat2}))
        ) as distance
        """
        result = self.client.execute(query)
        return result[0][0] if result else 0.0

    @abstractmethod
    def get_nearby_stations(self, lat: float, lon: float) -> pd.DataFrame:
        """Get nearby stations for a location.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            DataFrame with stations and distances
        """
        pass

    @abstractmethod
    def get_raw_data(self, source_ids: list[int], timestamp: datetime) -> pd.DataFrame:
        """Get raw data for stations and timestamp.

        Args:
            source_ids: List of station IDs
            timestamp: Timestamp to fetch data for

        Returns:
            DataFrame with raw data
        """
        pass

    def aggregate_weighted(
        self, df: pd.DataFrame, distances: pd.DataFrame, fields: list[str]
    ) -> dict:
        """Aggregate data using inverse distance weighting.

        Args:
            df: DataFrame with data
            distances: DataFrame with station distances
            fields: List of numeric fields to aggregate

        Returns:
            Dictionary with aggregated values
        """
        if df.empty:
            return {}

        # Merge with distances
        merged = df.merge(distances[["source_id", "distance_km"]], on="source_id", how="left")

        # Inverse distance weighting
        merged["weight"] = 1 / (merged["distance_km"] + 0.1)

        result = {}

        # Aggregate numeric fields
        for field in fields:
            if field in merged.columns:
                non_null = merged[merged[field].notna()]
                if not non_null.empty:
                    weighted_sum = (non_null[field] * non_null["weight"]).sum()
                    result[field] = weighted_sum / non_null["weight"].sum()
                else:
                    result[field] = None
            else:
                result[field] = None

        # Most common condition
        if "condition" in merged.columns:
            conditions = merged["condition"].dropna()
            if not conditions.empty:
                result["condition"] = (
                    conditions.mode().iloc[0] if not conditions.mode().empty else None
                )
            else:
                result["condition"] = None
        else:
            result["condition"] = None

        return result

    def calculate_station_quality(self, num_stations: int) -> float:
        """Calculate quality score based on number of stations.

        Args:
            num_stations: Number of stations used

        Returns:
            Quality factor between 0.0 and 1.0
        """
        # Normalize to 3 stations (ideal)
        return min(num_stations / 3.0, 1.0)

    @abstractmethod
    def transform_for_postal_code(self, plz: str, timestamp: datetime) -> dict | None:
        """Transform data for a single postal code.

        Args:
            plz: Postal code
            timestamp: Timestamp to transform

        Returns:
            Dictionary with transformed data or None
        """
        pass

    def transform_batch(
        self,
        postal_codes: list[str],
        timestamps: list[datetime],
    ) -> pd.DataFrame:
        """Transform data for multiple postal codes and timestamps.

        Args:
            postal_codes: List of postal codes
            timestamps: List of timestamps

        Returns:
            DataFrame with transformed records
        """
        records = []

        for plz in postal_codes:
            for timestamp in timestamps:
                result = self.transform_for_postal_code(plz, timestamp)
                if result:
                    records.append(result)

        return pd.DataFrame(records) if records else pd.DataFrame()

    @abstractmethod
    def save_transformed_data(self, df: pd.DataFrame) -> int:
        """Save transformed data to staging table.

        Args:
            df: DataFrame with transformed data

        Returns:
            Number of records saved
        """
        pass
