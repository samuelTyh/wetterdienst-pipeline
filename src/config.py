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
    # Note: We use multiple databases (raw, staging), so no default database

    # BrightSky API settings
    brightsky_base_url: str = "https://api.brightsky.dev"

    # Prefect settings
    prefect_api_url: str = "http://localhost:4200/api"

    # Application settings
    postal_code_prefixes: list[str] = ["10", "12", "13"]  # e.g., "10", "12", "13" for Berlin
    max_distance: int = 10000

    @property
    def clickhouse_url(self) -> str:
        """Get ClickHouse connection URL."""
        return f"http://{self.clickhouse_host}:{self.clickhouse_port}"


# Global settings instance
settings = Settings()
