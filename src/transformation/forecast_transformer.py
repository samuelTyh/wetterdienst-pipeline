"""Forecast transformer."""

from datetime import datetime, timedelta

import pandas as pd

from src.database import operations
from src.transformation.base_transformer import BaseWeatherTransformer


class ForecastTransformer(BaseWeatherTransformer):
    """Transform forecasts to postal code level."""

    def get_nearby_stations(self, lat: float, lon: float) -> pd.DataFrame:
        """Get nearby forecast stations.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            DataFrame with forecast stations and distances
        """
        query = f"""
        SELECT
            id as source_id,
            station_name,
            lat,
            lon,
            6371 * acos(
                cos(radians({lat})) * cos(radians(lat)) *
                cos(radians(lon) - radians({lon})) +
                sin(radians({lat})) * sin(radians(lat))
            ) as distance_km
        FROM raw.weather_stations FINAL
        WHERE observation_type = 'forecast'
        HAVING distance_km <= {self.max_distance_km}
        ORDER BY distance_km
        """

        result = self.client.execute(query)
        if not result:
            return pd.DataFrame()

        return pd.DataFrame(result.named_results())

    def get_raw_data(self, source_ids: list[int], timestamp: datetime) -> pd.DataFrame:
        """Get forecasts for timestamp.

        Args:
            source_ids: List of station IDs
            timestamp: Timestamp to fetch forecasts for

        Returns:
            DataFrame with most recent forecasts
        """
        if not source_ids:
            return pd.DataFrame()

        source_ids_str = ",".join(str(sid) for sid in source_ids)

        query = f"""
        SELECT
            source_id,
            timestamp,
            temperature,
            precipitation,
            precipitation_probability,
            relative_humidity,
            wind_speed,
            wind_direction,
            pressure_msl,
            cloud_cover,
            sunshine,
            condition,
            forecast_created_at
        FROM raw.weather_forecasts FINAL
        WHERE source_id IN ({source_ids_str})
          AND timestamp = '{timestamp.strftime("%Y-%m-%d %H:%M:%S")}'
        ORDER BY forecast_created_at DESC
        """

        result = self.client.execute(query)
        if not result:
            return pd.DataFrame()

        df = pd.DataFrame(result.named_results())

        # Clean data
        df = self.cleaner.clean_forecasts(df)

        return df

    def transform_for_postal_code(self, plz: str, timestamp: datetime) -> dict | None:
        """Transform forecasts for a postal code.

        Args:
            plz: Postal code
            timestamp: Hour to transform

        Returns:
            Dictionary with transformed forecast or None
        """
        # Get postal code info
        postal_codes = self.get_postal_codes(prefix=plz[:2])
        postal_code = postal_codes[postal_codes["plz"] == plz]

        if postal_code.empty:
            return None

        lat = postal_code.iloc[0]["centroid_lat"]
        lon = postal_code.iloc[0]["centroid_lon"]

        # Get nearby stations
        stations = self.get_nearby_stations(lat, lon)

        if stations.empty:
            return None

        # Get forecasts
        fc_df = self.get_raw_data(stations["source_id"].tolist(), timestamp)

        if fc_df.empty or len(fc_df) < self.min_stations:
            return None

        # Aggregate numeric fields
        numeric_fields = [
            "temperature",
            "precipitation",
            "precipitation_probability",
            "relative_humidity",
            "wind_speed",
            "wind_direction",
            "pressure_msl",
            "cloud_cover",
            "sunshine",
        ]

        aggregated = self.aggregate_weighted(fc_df, stations, numeric_fields)

        if not aggregated:
            return None

        # Calculate quality score
        num_stations = len(fc_df)
        station_quality = self.calculate_station_quality(num_stations)

        # Average quality scores from individual forecasts
        if "quality_score" in fc_df.columns:
            data_quality = fc_df["quality_score"].mean()
        else:
            data_quality = 1.0

        final_quality = data_quality * station_quality

        # Validate aggregated result
        aggregated_series = pd.Series(aggregated)
        is_valid = self.cleaner.validate_row(aggregated_series)

        # Get most recent forecast_created_at
        forecast_created_at = fc_df["forecast_created_at"].max()

        return {
            "plz": plz,
            "timestamp": timestamp,
            "forecast_created_at": forecast_created_at,
            "temperature": aggregated.get("temperature"),
            "precipitation": aggregated.get("precipitation"),
            "precipitation_probability": aggregated.get("precipitation_probability"),
            "relative_humidity": aggregated.get("relative_humidity"),
            "wind_speed": aggregated.get("wind_speed"),
            "wind_direction": aggregated.get("wind_direction"),
            "pressure_msl": aggregated.get("pressure_msl"),
            "cloud_cover": aggregated.get("cloud_cover"),
            "sunshine": aggregated.get("sunshine"),
            "condition": aggregated.get("condition"),
            "num_stations": num_stations,
            "data_quality_score": final_quality,
            "is_validated": is_valid,
        }

    def save_transformed_data(self, df: pd.DataFrame) -> int:
        """Save transformed forecasts to staging table.

        Args:
            df: DataFrame with transformed forecasts

        Returns:
            Number of records saved
        """
        if df.empty:
            return 0

        operations.insert_forecasts_by_postal_code_df(df)
        return len(df)

    def transform(
        self,
        prefix: str | None = None,
        days_ahead: int = 7,
    ) -> int:
        """Transform forecasts for postal codes.

        Args:
            prefix: Optional postal code prefix filter
            days_ahead: Number of days ahead to transform

        Returns:
            Number of records transformed
        """
        print(f"Transforming forecasts (prefix: {prefix or 'all'}, days_ahead: {days_ahead})...")

        # Get postal codes
        postal_codes = self.get_postal_codes(prefix=prefix)

        if postal_codes.empty:
            print("No postal codes found")
            return 0

        print(f"Processing {len(postal_codes)} postal codes...")

        # Generate timestamps
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        timestamps = [now + timedelta(hours=h) for h in range(days_ahead * 24)]

        # Transform batch
        df = self.transform_batch(postal_codes["plz"].tolist(), timestamps)

        if df.empty:
            print("No records to save")
            return 0

        # Save
        print(f"Saving {len(df)} transformed forecasts...")
        count = self.save_transformed_data(df)

        print(f"✓ Successfully transformed {count} forecasts")
        return count


if __name__ == "__main__":
    from src.config import settings

    transformer = ForecastTransformer(max_distance_km=10.0, min_stations=1)

    total_count = 0
    for prefix in settings.postal_code_prefixes:
        print(f"\n{'=' * 60}")
        print(f"Processing prefix: {prefix}")
        print(f"{'=' * 60}")

        count = transformer.transform(prefix=prefix, days_ahead=7)
        total_count += count

    print(f"\n{'=' * 60}")
    print(f"Total transformed: {total_count} forecasts")
    print(f"{'=' * 60}")
