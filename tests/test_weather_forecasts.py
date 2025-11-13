#!/usr/bin/env python3
"""Test script for weather forecasts ingestion."""

import sys
from datetime import datetime

from src.config import settings
from src.database import operations
from src.ingestion.weather_forecasts import (
    fetch_forecasts_by_station,
    get_forecast_stations,
    get_ingested_forecasts,
    ingest_weather_forecasts,
    parse_forecasts,
)


def test_fetch_forecast_stations():
    """Test fetching forecast stations."""
    print("Test 1: Fetching forecast stations...")
    try:
        stations = get_forecast_stations(postal_code_prefix="10")

        if stations.empty:
            print("✗ No forecast stations found")
            print("  Run: docker-compose exec pipeline python -m src.ingestion.weather_stations")
            return False

        print(f"✓ Found {len(stations)} forecast stations")
        print(f"  Sample: {stations.iloc[0]['station_name']}")
        print(f"  Station ID: {stations.iloc[0]['id']}")

        assert all(stations["observation_type"] == "forecast"), (
            "All stations should have observation_type='forecast'"
        )

        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_fetch_forecasts():
    """Test fetching forecasts for a single station."""
    print("\nTest 2: Fetching forecasts for a single station...")
    try:
        stations = get_forecast_stations(postal_code_prefix="10")

        if stations.empty:
            print("✗ No stations to test with")
            return False

        source_id = stations.iloc[0]["id"]
        station_name = stations.iloc[0]["station_name"]

        forecasts, forecast_created_at = fetch_forecasts_by_station(source_id, days_ahead=7)

        if not forecasts:
            print(f"⚠ No forecasts for station {source_id} ({station_name})")
            return True

        print(f"✓ Fetched {len(forecasts)} forecast records")
        print(f"  Station: {source_id} ({station_name})")
        print(f"  Forecast created at: {forecast_created_at}")
        print(
            f"  Sample: temp={forecasts[0].get('temperature')}°C, time={forecasts[0].get('timestamp')}"
        )

        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_parse_forecasts():
    """Test parsing forecast data."""
    print("\nTest 3: Parsing forecast data...")
    try:
        stations = get_forecast_stations(postal_code_prefix="10")

        if stations.empty:
            print("✗ No stations to test with")
            return False

        source_id = stations.iloc[0]["id"]
        forecasts, forecast_created_at = fetch_forecasts_by_station(source_id, days_ahead=7)

        if not forecasts:
            print("⚠ No forecasts to parse")
            return True

        # Add forecast_created_at to forecasts
        for f in forecasts:
            f["forecast_created_at"] = forecast_created_at

        df = parse_forecasts(forecasts)

        if df.empty:
            print("✗ Parsing resulted in empty DataFrame")
            return False

        print(f"✓ Parsed {len(df)} forecast records")

        required = [
            "source_id",
            "timestamp",
            "temperature",
            "precipitation",
            "precipitation_probability",
            "forecast_created_at",
        ]
        missing = [col for col in required if col not in df.columns]
        if missing:
            print(f"✗ Missing columns: {missing}")
            return False

        print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"  Forecast created: {df['forecast_created_at'].iloc[0]}")

        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_ingest(prefix: str = "10"):
    """Test ingesting forecasts into database."""
    print(f"\nTest 4: Ingesting forecasts (prefix: {prefix})...")
    try:
        if not operations.test_connection():
            print("✗ Cannot connect to database")
            return False

        stations = get_forecast_stations(postal_code_prefix=prefix)

        if stations.empty:
            print(f"✗ No forecast stations found with prefix {prefix}")
            return False

        print(f"✓ Found {len(stations)} forecast stations")

        before_df = get_ingested_forecasts(limit=10000)
        before_count = len(before_df)
        print(f"  Forecasts in DB before: {before_count}")

        count = ingest_weather_forecasts(postal_code_prefix=prefix, days_ahead=7)

        if count == 0:
            print("⚠ No forecasts ingested")
            return True

        print(f"✓ Ingested {count} forecasts")

        after_df = get_ingested_forecasts(limit=10000)
        after_count = len(after_df)
        print(f"  Forecasts in DB after: {after_count}")
        print(f"  New forecasts: {after_count - before_count}")

        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_query():
    """Test querying forecasts from database."""
    print("\nTest 5: Querying forecasts...")
    try:
        df = get_ingested_forecasts(limit=100)

        if df.empty:
            print("✗ No forecasts found in database")
            return False

        print(f"✓ Retrieved {len(df)} forecasts")

        if "timestamp" in df.columns:
            print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

        if "source_id" in df.columns:
            print(f"  Unique stations: {df['source_id'].nunique()}")

        if "forecast_created_at" in df.columns:
            print(f"  Latest forecast issued: {df['forecast_created_at'].max()}")

        if len(df) > 0:
            print("\n  Sample forecasts:")
            cols = [
                "source_id",
                "timestamp",
                "temperature",
                "precipitation",
                "precipitation_probability",
            ]
            available = [c for c in cols if c in df.columns]
            print(df[available].head(3).to_string(index=False))

        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_statistics():
    """Test database statistics."""
    print("\nTest 6: Database statistics...")
    try:
        status = operations.get_database_status()
        counts = status.get("table_counts", {})

        forecast_count = counts.get("raw.weather_forecasts", 0)
        print(f"✓ Total forecasts in database: {forecast_count:,}")

        if "latest_ingestions" in status and "weather_forecasts" in status["latest_ingestions"]:
            timestamp = status["latest_ingestions"]["weather_forecasts"]
            print(f"✓ Latest ingestion: {timestamp}")

        if "forecast_date_range" in counts:
            date_range = counts["forecast_date_range"]
            print(f"✓ Forecast date range: {date_range[0]} to {date_range[1]}")

        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("Weather Forecasts Ingestion Test Suite")
    print("=" * 70)
    print(f"Configuration:")
    print(f"  ClickHouse host: {settings.clickhouse_host}")
    print(f"  BrightSky API: {settings.brightsky_base_url}")
    print(f"  Postal code prefixes: {settings.postal_code_prefixes}")
    print("=" * 70)

    results = []

    success = test_fetch_forecast_stations()
    results.append(("Fetch Forecast Stations", success))

    success = test_fetch_forecasts()
    results.append(("Fetch Forecasts", success))

    success = test_parse_forecasts()
    results.append(("Parse Forecasts", success))

    success = test_ingest()
    results.append(("Ingest Forecasts", success))

    if not success:
        print("\n✗ Skipping query tests due to ingestion failure")
    else:
        success = test_query()
        results.append(("Query Forecasts", success))

        success = test_statistics()
        results.append(("Statistics", success))

    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {name}")

    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 70)

    if passed == total:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print(f"\n✗ {total - passed} test(s) failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
