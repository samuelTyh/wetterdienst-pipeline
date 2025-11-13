#!/usr/bin/env python3
"""
Serve all Prefect flows.

This script serves all flows to the Prefect server, making them
visible and executable from the UI. It keeps running to serve the flows.

Usage:
    python scripts/serve_all_flows.py
"""

from prefect import serve

from flows.ingest_forecasts import ingest_forecasts_flow
from flows.ingest_observations import ingest_weather_observations_flow

# Import all flow functions
from flows.ingest_postal_codes import ingest_postal_codes_flow
from flows.ingest_weather_stations import ingest_weather_stations_flow
from flows.transform_forecasts import transform_forecasts_flow
from flows.transform_observations import transform_observations_flow


def main():
    """Serve all flows to Prefect server."""

    print("=" * 60)
    print("Starting Prefect Flow Server")
    print("=" * 60)
    print()

    # List of deployments to serve
    deployments = []

    # Postal Codes Ingestion (manual/one-time)
    print("-> Configuring: postal-codes-ingestion")
    deployments.append(
        ingest_postal_codes_flow.to_deployment(
            name="postal-codes-ingestion",
            description="One-time ingestion of German postal codes from GitHub",
            tags=["ingestion", "postal-codes", "one-time"],
            version="1.0",
        )
    )

    # Weather Stations Ingestion (manual/periodic)
    print("-> Configuring: weather-stations-ingestion")
    postal_code_prefix = [
        "10",
        # "12", "13"
    ]
    print(f"-> Weather stations ingestion for postal codes starting with: {postal_code_prefix}")
    for prefix in postal_code_prefix:
        deployments.append(
            ingest_weather_stations_flow.to_deployment(
                name=f"weather-stations-prefix-{prefix}",
                description="Ingest weather station metadata from BrightSky API",
                parameters={"prefix": f"{prefix}"},
                tags=["ingestion", "weather-stations", "manual"],
                version="1.0",
            )
        )

    # Weather Observations Ingestion (hourly)
    print("-> Configuring: current-weather-observations-hourly")
    for prefix in postal_code_prefix:
        deployments.append(
            ingest_weather_observations_flow.to_deployment(
                name=f"current-weather-observations-hourly-prefix-{prefix}",
                description=f"Hourly current weather from SYNOP stations (prefix {prefix})",
                parameters={"prefix": prefix},
                tags=["ingestion", "observations", "synop", "current-weather", "scheduled"],
                cron="0 * * * *",  # Every hour (DWD updates twice per hour)
                version="2.0",  # Updated to use /current_weather + SYNOP
            )
        )

    # Weather Forecasts Ingestion (every 6 hours)
    print("-> Configuring: forecasts-6hourly")
    for prefix in postal_code_prefix:
        deployments.append(
            ingest_forecasts_flow.to_deployment(
                name=f"forecasts-6hourly-prefix-{prefix}",
                description=f"7-day weather forecasts from BrightSky API (prefix {prefix})",
                parameters={"prefix": prefix, "days_ahead": 7},
                tags=["ingestion", "forecasts", "scheduled"],
                cron="0 */6 * * *",  # Every 6 hours
                version="1.0",
            )
        )

    # Observation Transformation (every hour)
    print("-> Configuring: transform-observations-2hourly")
    for prefix in postal_code_prefix:
        deployments.append(
            transform_observations_flow.to_deployment(
                name=f"transform-observations-hourly-prefix-{prefix}",
                description=f"Transform SYNOP observations to postal codes (prefix {prefix})",
                parameters={"prefix": prefix, "hours_back": 24},
                tags=["transformation", "observations", "scheduled"],
                cron="10 * * * *",  # Every hour at 10 minutes past the hour
                version="1.0",
            )
        )

    # Forecast Transformation (every hour)
    print("-> Configuring: transform-forecasts-2hourly")
    for prefix in postal_code_prefix:
        deployments.append(
            transform_forecasts_flow.to_deployment(
                name=f"transform-forecasts-hourly-prefix-{prefix}",
                description=f"Transform forecasts to postal codes (prefix {prefix})",
                parameters={"prefix": prefix, "days_ahead": 7},
                tags=["transformation", "forecasts", "scheduled"],
                cron="10 * * * *",  # Every hour at 10 minutes past the hour
                version="1.0",
            )
        )

    print()
    print(f"Total deployments: {len(deployments)}")
    print()
    print("=" * 60)
    print("Serving flows to Prefect server...")
    print("=" * 60)
    print()
    print("Flows are now visible in the UI at: http://localhost:4200")
    print("Go to 'Deployments' tab to see and run them.")
    print()
    print("This process will keep running. Press Ctrl+C to stop.")
    print()

    # Serve all deployments
    # This keeps the process running and serves the flows
    serve(*deployments)


if __name__ == "__main__":
    main()
