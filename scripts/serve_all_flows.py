#!/usr/bin/env python3
"""
Serve all Prefect flows.

This script serves all flows to the Prefect server, making them
visible and executable from the UI. It keeps running to serve the flows.

Usage:
    python scripts/serve_all_flows.py
"""

from prefect import serve

from flows.ingest_observations import ingest_weather_observations_flow

# Import all flow functions
# from flows.ingest_postal_codes import ingest_postal_codes_flow
from flows.ingest_weather_stations import ingest_weather_stations_flow

# Note: Import other flows as they are created
# from flows.ingest_forecasts import ingest_forecasts_flow
# from flows.transform_weather import transform_weather_flow


def main():
    """Serve all flows to Prefect server."""

    print("=" * 60)
    print("Starting Prefect Flow Server")
    print("=" * 60)
    print()

    # List of deployments to serve
    deployments = []

    # Postal Codes Ingestion (manual/one-time)
    # print("→ Configuring: postal-codes-ingestion")
    # deployments.append(
    #     ingest_postal_codes_flow.to_deployment(
    #         name="postal-codes-ingestion",
    #         description="One-time ingestion of German postal codes from GitHub",
    #         tags=["ingestion", "postal-codes", "one-time"],
    #         version="1.0",
    #     )
    # )

    # Weather Stations Ingestion (manual/periodic)
    print("→ Configuring: weather-stations-ingestion")
    berlin_postal_code_prefix = ["10", "12", "13"]
    print(f"→ Berlin weather stations ingestion: {berlin_postal_code_prefix}")
    for prefix in berlin_postal_code_prefix:
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
    print("→ Configuring: observations-hourly")
    for prefix in berlin_postal_code_prefix:
        deployments.append(
            ingest_weather_observations_flow.to_deployment(
                name=f"observations-hourly-prefix-{prefix}",
                description=f"Hourly weather observations ingestion for prefix {prefix}",
                parameters={"prefix": prefix},
                tags=["ingestion", "observations", "scheduled"],
                cron="0 * * * *",  # Every hour
                version="1.0",
            )
        )

    # Weather Forecasts Ingestion (every 6 hours)
    # Uncomment when flow is created:
    # print("→ Configuring: forecasts-6hourly")
    # deployments.append(
    #     ingest_forecasts_flow.to_deployment(
    #         name="forecasts-6hourly",
    #         description="Weather forecasts ingestion every 6 hours from BrightSky API",
    #         tags=["ingestion", "forecasts", "scheduled"],
    #         cron="0 */6 * * *",  # Every 6 hours
    #         version="1.0",
    #     )
    # )

    # Weather Data Transformation (every 2 hours)
    # Uncomment when flow is created:
    # print("→ Configuring: transform-weather-2hourly")
    # deployments.append(
    #     transform_weather_flow.to_deployment(
    #         name="transform-weather-2hourly",
    #         description="Transform raw weather data to staging tables every 2 hours",
    #         tags=["transformation", "scheduled"],
    #         cron="0 */2 * * *",  # Every 2 hours
    #         version="1.0",
    #     )
    # )

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
