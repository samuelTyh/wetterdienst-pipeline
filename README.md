# Weather Data Ingestion Pipeline

## Project Structure

```
weather-pipeline/
├── src/
│   ├── __init__.py
│   ├── config.py                   # Configuration management
│   ├── database/
│   │   ├── __init__.py
│   │   ├── clickhouse_client.py    # ClickHouse connection helper
│   │   ├── operations.py           # ClickHouse operations
│   │   └── schema.py               # Database schema definitions
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── postal_codes.py         # Postal code data ingestion
│   │   ├── weather_observations.py # Weather observations ingestion
│   │   └── weather_forecasts.py    # Weather forecasts ingestion
│   ├── transformation/
│   │   ├── __init__.py
│   │   ├── cleaners.py             # Data cleaning functions
│   │   └── aggregators.py          # Data aggregation logic
│   └── utils/
│       ├── __init__.py
│       └── geo.py                  # Geospatial utilities
├── flows/
│   ├── __init__.py
│   ├── ingest_postal_codes.py      # Prefect flow for postal codes
│   ├── ingest_observations.py      # Prefect flow for observations
│   ├── ingest_forecasts.py         # Prefect flow for forecasts
│   └── transform_weather.py        # Prefect flow for transformations
├── clickhouse/
│   └── init/
│       └── 01_init.sql             # Initial database schema
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
- **PostgreSQL 15**: Prefect metadata database
- **ClickHouse**: High-performance columnar database for time-series and analytical queries
- **Prefect 3**: Modern workflow orchestration framework with separate server and worker
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
chmod +x scripts/service.sh
./scripts/service.sh start
```

3. Wait for services to be healthy (30-60 seconds):
```bash
# Check status
./scripts/service.sh status

# Watch logs
./scripts/service.sh logs
```

4. Create a work pool in Prefect UI (optional):
```bash
# Access Prefect UI at http://localhost:4200
# Or create work pool via CLI:
docker-compose exec prefect-server prefect work-pool create default-pool --type process
```

5. Access services:
- **Prefect UI**: http://localhost:4200
- **ClickHouse**: http://localhost:8123 (user: weather_user, password: weather_pass)
- **PostgreSQL**: localhost:5432 (user: prefect, password: prefect_pass)

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

**ClickHouse:**
- `CLICKHOUSE_HOST`: ClickHouse server host (default: clickhouse)
- `CLICKHOUSE_PORT`: ClickHouse server port (default: 8123)
- `CLICKHOUSE_USER`: Database user (default: weather_user)
- `CLICKHOUSE_PASSWORD`: Database password (default: weather_pass)
- `CLICKHOUSE_DATABASE`: Database name (default: weather)

**Prefect:**
- `PREFECT_API_URL`: Prefect API URL for workers (default: http://prefect-server:4200/api)
- `PREFECT_UI_API_URL`: Prefect API URL for browser UI (default: http://localhost:4200/api)
- `PREFECT_API_DATABASE_CONNECTION_URL`: PostgreSQL connection string

**Application:**
- `POSTAL_CODE_PREFIX`: Postal code prefix to filter (e.g., "10" for Berlin)
- `BRIGHTSKY_BASE_URL`: BrightSky API base URL (default: https://api.brightsky.dev)

## Next Steps

The following components will be implemented:
1. Database schema and models
2. Postal code ingestion
3. Weather observations ingestion
4. Weather forecasts ingestion
5. Data transformation and cleaning
6. Prefect flows and scheduling
