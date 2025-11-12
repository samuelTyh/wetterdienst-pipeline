#!/usr/bin/env python3
"""Test script for weather station ingestion."""

import sys

from src.config import settings
from src.database import operations
from src.ingestion.weather_stations import (
    fetch_stations_by_location,
    get_ingested_stations,
    ingest_weather_stations,
    parse_stations,
)


def test_fetch_single_location():
    """Test fetching stations for a single location (Berlin center)."""
    print("Test 1: Fetching stations near Berlin center...")
    try:
        # Berlin coordinates
        lat, lon = 52.52, 13.40
        stations = fetch_stations_by_location(lat, lon, max_distance=10000)

        if not stations:
            print("✗ No stations found")
            return False

        print(f"✓ Fetched {len(stations)} stations")
        print(f"  Sample station: {stations[0].get('station_name', 'Unknown')}")
        print(f"  Station ID: {stations[0].get('id')}")
        print(f"  Observation type: {stations[0].get('observation_type')}")

        return True
    except Exception as e:
        print(f"✗ Fetch failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_parse_stations():
    """Test parsing station data."""
    print("\nTest 2: Parsing station data...")
    try:
        # Fetch some stations first
        lat, lon = 52.52, 13.40
        stations = fetch_stations_by_location(lat, lon, max_distance=10000)

        if not stations:
            print("✗ No stations to parse")
            return False

        # Parse
        df = parse_stations(stations)

        if df.empty:
            print("✗ Parsing resulted in empty DataFrame")
            return False

        print(f"✓ Parsed {len(df)} stations")
        print(f"  Columns: {list(df.columns)}")

        # Verify required columns
        required = [
            "id",
            "dwd_station_id",
            "wmo_station_id",
            "station_name",
            "observation_type",
            "lat",
            "lon",
            "height",
            "first_record",
            "last_record",
            "distance",
        ]
        missing = [col for col in required if col not in df.columns]
        if missing:
            print(f"✗ Missing columns: {missing}")
            return False

        # Verify data types
        if df["first_record"].isna().all() or df["last_record"].isna().all():
            print("✗ DateTime fields not parsed correctly")
            return False

        print("✓ All validations passed")
        print(f"\nObservation types found:")
        print(df["observation_type"].value_counts())

        return True
    except Exception as e:
        print(f"✗ Parse failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_ingest(prefix: str = "10"):
    """Test ingesting weather stations into database."""
    print(f"\nTest 3: Ingesting weather stations (prefix: {prefix})...")
    try:
        # Check connection first
        if not operations.test_connection():
            print("✗ Cannot connect to database")
            return False

        # Check postal codes exist
        postal_codes = operations.get_postal_codes(prefix=prefix)
        if postal_codes.empty:
            print(f"✗ No postal codes found with prefix {prefix}")
            print("  Run postal code ingestion first:")
            print("  docker-compose exec pipeline python tests/test_postal_codes.py")
            return False

        print(f"✓ Found {len(postal_codes)} postal codes")

        # Ingest stations
        count = ingest_weather_stations(postal_code_prefix=prefix, max_distance=10000)

        if count == 0:
            print("✗ No stations ingested")
            return False

        print(f"✓ Ingested {count} weather stations")

        # Verify in database
        df = get_ingested_stations(postal_code_prefix=prefix)
        db_count = len(df)
        print(f"✓ Found {db_count} stations in database")

        if db_count < count:
            print(f"⚠ Warning: Expected {count} but found {db_count}")

        return True
    except Exception as e:
        print(f"✗ Ingestion failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_query(prefix: str = "10"):
    """Test querying weather stations."""
    print(f"\nTest 4: Querying weather stations (prefix: {prefix})...")
    try:
        df = get_ingested_stations(postal_code_prefix=prefix)

        if df.empty:
            print("✗ No stations found in database")
            return False

        print(f"✓ Retrieved {len(df)} stations")

        # Show observation type breakdown
        print("\nObservation types:")
        print(df["observation_type"].value_counts())

        # Show sample data
        if len(df) > 0:
            print("\nSample stations:")
            print(df[["id", "station_name", "observation_type", "lat", "lon"]].head(3))

        # Test filtering by observation type
        obs_df = get_ingested_stations(observation_type="observation", postal_code_prefix=prefix)
        print(f"\n✓ Found {len(obs_df)} observation-type stations")

        return True
    except Exception as e:
        print(f"✗ Query failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_statistics():
    """Test database statistics."""
    print("\nTest 5: Database statistics...")
    try:
        status = operations.get_database_status()
        counts = status.get("table_counts", {})

        station_count = counts.get("raw.weather_stations", 0)
        print(f"✓ Total weather stations in database: {station_count:,}")

        if "latest_ingestions" in status and "weather_stations" in status["latest_ingestions"]:
            timestamp = status["latest_ingestions"]["weather_stations"]
            print(f"✓ Latest ingestion: {timestamp}")

        return True
    except Exception as e:
        print(f"✗ Statistics failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("Weather Station Ingestion Test Suite")
    print("=" * 70)
    print(f"Configuration:")
    print(f"  ClickHouse host: {settings.clickhouse_host}")
    print(f"  BrightSky API: {settings.brightsky_base_url}")
    print(f"  Postal code prefix: {settings.postal_code_prefix or 'all'}")
    print("=" * 70)

    results = []

    # Test 1: Fetch single location
    success = test_fetch_single_location()
    results.append(("Fetch Single Location", success))

    if not success:
        print("\n⚠ Continuing despite fetch failure (may be network issue)")

    # Test 2: Parse
    success = test_parse_stations()
    results.append(("Parse Stations", success))

    # Test 3: Ingest
    success = test_ingest()
    results.append(("Ingest Stations", success))

    if not success:
        print("\n✗ Skipping query tests due to ingestion failure")
    else:
        # Test 4: Query
        success = test_query()
        results.append(("Query Stations", success))

        # Test 5: Statistics
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
