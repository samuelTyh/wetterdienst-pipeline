# Weather Data Pipeline

Data ingestion and transformation pipeline for weather data in Berlin area using BrightSky API.

## Architecture

```
BrightSky API → Ingestion → ClickHouse (raw) → Transformation → ClickHouse (staging)
                    ↓                                ↓
                 Prefect                          Prefect
```

## Stack

- **Python 3.13** + **uv** (package manager)
- **ClickHouse** (time-series data storage)
- **PostgreSQL** (Prefect metadata)
- **Prefect 3** (workflow orchestration)
- **Docker Compose** (deployment)

## Quick Start

```bash
# 1. Clone and setup
git clone git@github.com:samuelTyh/wetterdienst-pipeline.git
cd wetterdienst-pipeline
uv sync

# 2. Start services
chmod +x ./scripts/service.sh
./scripts/service.sh start

# 3. Wait for initialization (~60s)
./scripts/service.sh logs

# 4. Access Prefect UI
open http://localhost:4200/dashboard
```

## Project Structure

```
src/
├── ingestion/                        # Data ingestion modules
│   ├── postal_codes.py               # Postal codes from GitHub
│   ├── weather_stations.py           # Stations from BrightSky
│   ├── weather_observations.py       # SYNOP current weather
│   └── weather_forecasts.py          # 7-day forecasts
├── transformation/                   # OOP-based transformers
│   ├── cleaner.py                    # Data validation & quality scoring
│   ├── base_transformer.py           # Abstract base
│   ├── observation_transformer.py    # SYNOP → postal code
│   └── forecast_transformer.py       # Forecasts → postal code
└── database/
    ├── clickhouse_client.py          # ClickHouse client
    ├── operations.py                 # ClickHouse CRUD operations
    └── schema.py                     # Pydantic models

flows/
├── ingest_*.py                       # Ingestion flows
└── transform_*.py                    # Transformation flows

scripts/
└── serve_all_flows.py                # Registers all Prefect flows deployments
```

## Data Flow

### Ingestion (Raw Layer)
1. **Postal Codes** → `raw.postal_codes` (The data ingestion runs directly after the service spinning up)
2. **Weather Stations** → `raw.weather_stations` (Should be run manually after the service is up)
3. **SYNOP Observations** → `raw.weather_observations_synop` (hourly, 10-min resolution)
4. **Forecasts** → `raw.weather_forecasts` (6-hourly, 7 days ahead)

### Transformation (Staging Layer)
1. **Observation Aggregation** → `staging.observations_by_postal_code`
   - Distance-weighted averaging from nearby SYNOP stations (10km radius)
   - Data validation (temp, precip, humidity, wind ranges)
   - Quality scoring (0.0-1.0)

2. **Forecast Aggregation** → `staging.forecasts_by_postal_code`
   - Distance-weighted averaging from nearby forecast stations
   - Quality scoring based on station count + data completeness

## Prefect Deployments (6 Total)

| Flow | Schedule | Description |
|------|----------|-------------|
| `postal-codes-ingestion` | Manual | Load Berlin postal codes |
| `weather-stations-prefix-10` | Manual | Discover weather stations |
| `observations-hourly-prefix-10` | Hourly | Ingest SYNOP current weather |
| `forecasts-6hourly-prefix-10` | 6-hourly | Ingest 7-day forecasts |
| `transform-observations-prefix-10` | hourly | Aggregate to postal codes |
| `transform-forecasts-prefix-10` | 6-hourly | Aggregate to postal codes |

## Configuration

Edit `src/config.py` or set environment variables:

```python
CLICKHOUSE_HOST=clickhouse          # ClickHouse server
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=weather_user
CLICKHOUSE_PASSWORD=weather_pass

BRIGHTSKY_BASE_URL=https://api.brightsky.dev
POSTAL_CODE_PREFIXES=["10", "12", "13"]  # Berlin prefixes
MAX_DISTANCE=10000  # Station search radius (meters)
```

## Running Manually

```bash
# Test ingestion
uv run python -m src.ingestion.postal_codes
uv run python -m src.ingestion.weather_stations
uv run python -m src.ingestion.weather_observations
uv run python -m src.ingestion.weather_forecasts

# Test transformation
uv run python -m src.transformation.observation_transformer
uv run python -m src.transformation.forecast_transformer

# Run via Prefect flow
uv run python flows/ingest_forecasts.py
uv run python flows/transform_observations_flow.py
```

## Database Access

```bash
# ClickHouse CLI
docker-compose exec clickhouse clickhouse-client

# Query data
SELECT count() FROM raw.postal_codes;
SELECT count() FROM raw.weather_stations;
SELECT count() FROM raw.weather_observations_synop;
SELECT count() FROM raw.weather_forecasts;
SELECT count() FROM staging.observations_by_postal_code;
SELECT count() FROM staging.forecasts_by_postal_code;
```

## Development

```bash
# Install dependencies
uv sync --dev

# Run tests
uv run python tests/test_weather_observations.py
uv run python tests/test_weather_forecasts.py

# Format code
uv run ruff format .

# Lint
uv run ruff check .
```

## Services

- **Prefect UI**: http://localhost:4200
- **ClickHouse HTTP**: http://localhost:8123 (user: weather_user, pass: weather_pass)
- **PostgreSQL**: localhost:5432 (user: prefect, pass: prefect_pass)

## Troubleshooting

```bash
# Check service health
./scripts/service.sh status

# Restart services
./scripts/service.sh restart
```

## Key Features

✅ **OOP Architecture** - Clean transformer classes with inheritance
✅ **Data Validation** - Range checks and quality scoring
✅ **Distance-Weighted Aggregation** - Inverse distance weighting
✅ **Scheduled Execution** - Automatic via Prefect cron schedules
✅ **Modular Design** - Easy to extend with new data sources
✅ **Production Ready** - Docker-based, health checks, logging

## Data Volumes

- **Postal codes**: 8172 records

Filter by postal code prefix "10"
- **Weather stations**: 82 records for all observation types
- **Observations**: 4 records/hour from 4 weather stations
- **Forecasts**: 1350 records/6hours from 9 weather stations (7-day window, hourly granularity)
- **Staging**: 59 observations + 8732 forecasts (7-day window, hourly granularity)
