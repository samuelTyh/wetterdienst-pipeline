"""Configuration management using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ClickHouse settings
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_user: str = "weather_user"
    clickhouse_password: str = "weather_pass"
    clickhouse_database: str = "weather"

    # BrightSky API settings
    brightsky_base_url: str = "https://api.brightsky.dev"

    # Postal code filtering (e.g., "10" for Berlin, "80" for Munich)
    postal_code_prefix: str = "10"

    # Prefect settings
    prefect_api_url: str = "http://localhost:4200/api"

    @property
    def clickhouse_url(self) -> str:
        """Get ClickHouse connection URL."""
        return f"http://{self.clickhouse_host}:{self.clickhouse_port}"


# Global settings instance
settings = Settings()
