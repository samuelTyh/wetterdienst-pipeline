# Weather Data Ingestion Pipeline

## Project Structure

```
weather-pipeline/
├── src/
│   ├── __init__.py
│   ├── config.py                 # Configuration management
│   ├── database/
│   │   ├── __init__.py
│   │   ├── clickhouse_client.py  # ClickHouse connection and operations
│   │   └── schema.py              # Database schema definitions
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── postal_codes.py        # Postal code data ingestion
│   │   ├── weather_observations.py # Weather observations ingestion
│   │   └── weather_forecasts.py   # Weather forecasts ingestion
│   ├── transformation/
│   │   ├── __init__.py
│   │   ├── cleaners.py            # Data cleaning functions
│   │   └── aggregators.py         # Data aggregation logic
│   └── utils/
│       ├── __init__.py
│       └── geo.py                 # Geospatial utilities
├── flows/
│   ├── __init__.py
│   ├── ingest_postal_codes.py     # Prefect flow for postal codes
│   ├── ingest_observations.py     # Prefect flow for observations
│   ├── ingest_forecasts.py        # Prefect flow for forecasts
│   └── transform_weather.py       # Prefect flow for transformations
├── clickhouse/
│   └── init/
│       └── 01_init.sql            # Initial database schema
├── tests/
│   └── __init__.py
├── .python-version
├── pyproject.toml
├── docker-compose.yml
├── Dockerfile
├── .gitignore
├── README.md
└── handoff.md
```

## Technology Stack

- **Python 3.13**: Latest Python version
- **uv**: Fast Python package manager
- **ClickHouse**: High-performance columnar database for time-series and analytical queries
- **Prefect**: Modern workflow orchestration framework
- **Docker Compose**: Container orchestration for easy deployment
- **httpx**: Modern async HTTP client for API calls
- **pandas/geopandas**: Data manipulation and geospatial operations

## Quick Start

1. Initialize the project:
```bash
# Install uv if not already installed
pip install uv

# Sync dependencies
uv sync
```

2. Start the services:
```bash
docker-compose up -d
```

3. Access services:
- ClickHouse: http://localhost:8123
- Prefect UI: http://localhost:4200

## Development Setup

```bash
# Create virtual environment and install dependencies
uv sync --dev

# Run tests
uv run pytest

# Format code
uv run ruff format .

# Lint code
uv run ruff check .
```

## Configuration

Environment variables can be set in docker-compose.yml or via .env file:
- `CLICKHOUSE_HOST`: ClickHouse server host
- `CLICKHOUSE_PORT`: ClickHouse server port
- `CLICKHOUSE_USER`: Database user
- `CLICKHOUSE_PASSWORD`: Database password
- `CLICKHOUSE_DATABASE`: Database name
- `POSTAL_CODE_PREFIX`: Postal code prefix to filter (e.g., "10" for Berlin)
- `BRIGHTSKY_BASE_URL`: BrightSky API base URL

## Next Steps

The following components will be implemented:
1. Database schema and models
2. Postal code ingestion
3. Weather observations ingestion
4. Weather forecasts ingestion
5. Data transformation and cleaning
6. Prefect flows and scheduling
