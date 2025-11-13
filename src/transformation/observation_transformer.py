"""Observation transformer for SYNOP data."""

from datetime import datetime, timedelta

import pandas as pd

from src.database import operations
from src.transformation.base_transformer import BaseWeatherTransformer


class ObservationTransformer(BaseWeatherTransformer):
    """Transform SYNOP observations to postal code level."""

    def get_nearby_stations(self, lat: float, lon: float) -> pd.DataFrame:
        """Get nearby SYNOP stations.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            DataFrame with SYNOP stations and distances
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
        WHERE observation_type = 'synop'
        HAVING distance_km <= {self.max_distance_km}
        ORDER BY distance_km
        """

        result = self.client.execute(query)
        if not result:
            return pd.DataFrame()

        return pd.DataFrame(result.named_results())

    def get_raw_data(self, source_ids: list[int], timestamp: datetime) -> pd.DataFrame:
        """Get SYNOP observations for hour.

        Args:
            source_ids: List of station IDs
            timestamp: Hour to fetch (rounded to hour)

        Returns:
            DataFrame with observations
        """
        if not source_ids:
            return pd.DataFrame()

        # Round to hour
        hour_start = timestamp.replace(minute=0, second=0, microsecond=0)
        hour_end = hour_start + timedelta(hours=1)

        source_ids_str = ",".join(str(sid) for sid in source_ids)

        query = f"""
        SELECT
            source_id,
            timestamp,
            temperature,
            precipitation_60 as precipitation,
            relative_humidity,
            wind_speed_60 as wind_speed,
            wind_direction_60 as wind_direction,
            pressure_msl,
            cloud_cover,
            sunshine_60 as sunshine,
            condition
        FROM raw.weather_observations_synop FINAL
        WHERE source_id IN ({source_ids_str})
          AND timestamp >= '{hour_start.strftime("%Y-%m-%d %H:%M:%S")}'
          AND timestamp < '{hour_end.strftime("%Y-%m-%d %H:%M:%S")}'
        ORDER BY timestamp DESC
        """

        result = self.client.execute(query)
        if not result:
            return pd.DataFrame()

        df = pd.DataFrame(result.named_results())

        # Clean data
        df = self.cleaner.clean_observations(df)

        return df

    def transform_for_postal_code(self, plz: str, timestamp: datetime) -> dict | None:
        """Transform SYNOP observations for a postal code.

        Args:
            plz: Postal code
            timestamp: Hour to transform

        Returns:
            Dictionary with transformed observation or None
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

        # Get observations
        obs_df = self.get_raw_data(stations["source_id"].tolist(), timestamp)

        if obs_df.empty or len(obs_df) < self.min_stations:
            return None

        # Aggregate numeric fields
        numeric_fields = [
            "temperature",
            "precipitation",
            "relative_humidity",
            "wind_speed",
            "wind_direction",
            "pressure_msl",
            "cloud_cover",
            "sunshine",
        ]

        aggregated = self.aggregate_weighted(obs_df, stations, numeric_fields)

        if not aggregated:
            return None

        # Calculate quality score
        num_stations = len(obs_df)
        station_quality = self.calculate_station_quality(num_stations)

        # Average quality scores from individual observations
        if "quality_score" in obs_df.columns:
            data_quality = obs_df["quality_score"].mean()
        else:
            data_quality = 1.0

        final_quality = data_quality * station_quality

        # Validate aggregated result
        aggregated_series = pd.Series(aggregated)
        is_valid = self.cleaner.validate_row(aggregated_series)

        return {
            "plz": plz,
            "timestamp": timestamp.replace(minute=0, second=0, microsecond=0),
            "temperature": aggregated.get("temperature"),
            "precipitation": aggregated.get("precipitation"),
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
        """Save transformed observations to staging table.

        Args:
            df: DataFrame with transformed observations

        Returns:
            Number of records saved
        """
        if df.empty:
            return 0

        operations.insert_observations_by_postal_code_df(df)
        return len(df)

    def transform(
        self,
        prefix: str | None = None,
        hours_back: int = 24,
    ) -> int:
        """Transform observations for postal codes.

        Args:
            prefix: Optional postal code prefix filter
            hours_back: Number of hours back to transform

        Returns:
            Number of records transformed
        """
        print(f"Transforming observations (prefix: {prefix or 'all'}, hours_back: {hours_back})...")

        # Get postal codes
        postal_codes = self.get_postal_codes(prefix=prefix)

        if postal_codes.empty:
            print("No postal codes found")
            return 0

        print(f"Processing {len(postal_codes)} postal codes...")

        # Generate timestamps
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        timestamps = [now - timedelta(hours=h) for h in range(hours_back)]

        # Transform batch
        df = self.transform_batch(postal_codes["plz"].tolist(), timestamps)

        if df.empty:
            print("No records to save")
            return 0

        # Save
        print(f"Saving {len(df)} transformed observations...")
        count = self.save_transformed_data(df)

        print(f"✓ Successfully transformed {count} observations")
        return count


if __name__ == "__main__":
    from src.config import settings

    transformer = ObservationTransformer(max_distance_km=10.0, min_stations=1)

    total_count = 0
    for prefix in settings.postal_code_prefixes:
        print(f"\n{'=' * 60}")
        print(f"Processing prefix: {prefix}")
        print(f"{'=' * 60}")

        count = transformer.transform(prefix=prefix, hours_back=24)
        total_count += count

    print(f"\n{'=' * 60}")
    print(f"Total transformed: {total_count} observations")
    print(f"{'=' * 60}")
