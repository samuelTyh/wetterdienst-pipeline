"""Data cleaning and validation utilities."""

import pandas as pd


class WeatherDataCleaner:
    """Clean and validate weather data."""

    def __init__(
        self,
        temp_range: tuple[float, float] = (-30.0, 50.0),
        precip_range: tuple[float, float] = (0.0, 200.0),
        humidity_range: tuple[float, float] = (0.0, 100.0),
        wind_range: tuple[float, float] = (0.0, 200.0),
        pressure_range: tuple[float, float] = (800.0, 1100.0),
    ):
        """Initialize cleaner with validation ranges.

        Args:
            temp_range: Temperature range in °C
            precip_range: Precipitation range in mm
            humidity_range: Relative humidity range in %
            wind_range: Wind speed range in km/h
            pressure_range: Pressure range in hPa
        """
        self.temp_range = temp_range
        self.precip_range = precip_range
        self.humidity_range = humidity_range
        self.wind_range = wind_range
        self.pressure_range = pressure_range

    def validate_temperature(self, value: float | None) -> bool:
        """Validate temperature value."""
        if value is None:
            return True
        return self.temp_range[0] <= value <= self.temp_range[1]

    def validate_precipitation(self, value: float | None) -> bool:
        """Validate precipitation value."""
        if value is None:
            return True
        return self.precip_range[0] <= value <= self.precip_range[1]

    def validate_humidity(self, value: float | None) -> bool:
        """Validate humidity value."""
        if value is None:
            return True
        return self.humidity_range[0] <= value <= self.humidity_range[1]

    def validate_wind_speed(self, value: float | None) -> bool:
        """Validate wind speed value."""
        if value is None:
            return True
        return self.wind_range[0] <= value <= self.wind_range[1]

    def validate_pressure(self, value: float | None) -> bool:
        """Validate pressure value."""
        if value is None:
            return True
        return self.pressure_range[0] <= value <= self.pressure_range[1]

    def validate_row(self, row: pd.Series) -> bool:
        """Validate all fields in a data row.

        Args:
            row: DataFrame row with weather data

        Returns:
            True if all validations pass
        """
        checks = []

        if "temperature" in row:
            checks.append(self.validate_temperature(row["temperature"]))

        if "precipitation" in row:
            checks.append(self.validate_precipitation(row["precipitation"]))

        if "relative_humidity" in row:
            checks.append(self.validate_humidity(row["relative_humidity"]))

        if "wind_speed" in row:
            checks.append(self.validate_wind_speed(row["wind_speed"]))

        if "pressure_msl" in row:
            checks.append(self.validate_pressure(row["pressure_msl"]))

        return all(checks)

    def calculate_quality_score(self, row: pd.Series) -> float:
        """Calculate data quality score for a row.

        Args:
            row: DataFrame row with weather data

        Returns:
            Quality score between 0.0 and 1.0
        """
        score = 1.0

        # Validation penalties
        if "temperature" in row and not self.validate_temperature(row["temperature"]):
            score *= 0.5

        if "precipitation" in row and not self.validate_precipitation(row["precipitation"]):
            score *= 0.5

        if "relative_humidity" in row and not self.validate_humidity(row["relative_humidity"]):
            score *= 0.7

        if "wind_speed" in row and not self.validate_wind_speed(row["wind_speed"]):
            score *= 0.7

        if "pressure_msl" in row and not self.validate_pressure(row["pressure_msl"]):
            score *= 0.7

        # Completeness check
        critical_fields = ["temperature", "precipitation", "relative_humidity"]
        available_fields = [f for f in critical_fields if f in row.index]
        if available_fields:
            missing_count = sum(1 for f in available_fields if pd.isna(row[f]))
            completeness = 1 - (missing_count / len(available_fields))
            score *= 0.7 + 0.3 * completeness  # 70% base + 30% completeness bonus

        return score

    def clean_dataframe(self, df: pd.DataFrame, add_validation_cols: bool = True) -> pd.DataFrame:
        """Clean and validate a DataFrame of weather data.

        Args:
            df: DataFrame with weather data
            add_validation_cols: Whether to add is_valid and quality_score columns

        Returns:
            Cleaned DataFrame
        """
        if df.empty:
            return df

        df_clean = df.copy()

        # Remove duplicates
        if "source_id" in df_clean.columns and "timestamp" in df_clean.columns:
            df_clean = df_clean.drop_duplicates(subset=["source_id", "timestamp"])

        # Add validation columns
        if add_validation_cols:
            df_clean["is_valid"] = df_clean.apply(self.validate_row, axis=1)
            df_clean["quality_score"] = df_clean.apply(self.calculate_quality_score, axis=1)

        return df_clean

    def remove_invalid_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove rows that fail validation.

        Args:
            df: DataFrame with is_valid column

        Returns:
            DataFrame with only valid rows
        """
        if df.empty or "is_valid" not in df.columns:
            return df

        return df[df["is_valid"]].copy()

    def clean_observations(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean SYNOP observation data.

        Args:
            df: DataFrame with SYNOP observations

        Returns:
            Cleaned DataFrame
        """
        return self.clean_dataframe(df, add_validation_cols=True)

    def clean_forecasts(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean forecast data.

        Args:
            df: DataFrame with forecasts

        Returns:
            Cleaned DataFrame
        """
        df_clean = self.clean_dataframe(df, add_validation_cols=True)

        # Additional forecast-specific validation
        if "precipitation_probability" in df_clean.columns:
            df_clean.loc[
                (df_clean["precipitation_probability"] < 0)
                | (df_clean["precipitation_probability"] > 100),
                "is_valid",
            ] = False

        return df_clean


def get_default_cleaner() -> WeatherDataCleaner:
    """Get a cleaner instance with default parameters.

    Returns:
        WeatherDataCleaner instance
    """
    return WeatherDataCleaner()
