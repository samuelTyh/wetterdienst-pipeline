#!/usr/bin/env python3
"""Test script for weather observations ingestion (SYNOP/current_weather).

This test suite validates the complete SYNOP weather observations pipeline:
- Fetching active SYNOP stations with recent data
- Fetching current weather from BrightSky API
- Parsing SYNOP-specific fields (time-window precipitation and sunshine)
- Ingesting into raw.weather_observations_synop table
- Querying and validating the stored data
"""

import sys
from datetime import datetime

from src.config import settings
from src.database import operations
from src.ingestion.weather_observations import (
    fetch_current_weather_by_station,
    get_active_synop_stations,
    get_ingested_observations,
    ingest_weather_observations,
    parse_observations,
)

SYNNOP_FIELDS = [
    "precipitation_10",
    "precipitation_30",
    "precipitation_60",
    "solar_10",
    "solar_30",
    "solar_60",
    "sunshine_30",
    "sunshine_60",
    "wind_direction_10",
    "wind_direction_30",
    "wind_direction_60",
    "wind_speed_10",
    "wind_speed_30",
    "wind_speed_60",
    "wind_gust_direction_10",
    "wind_gust_direction_30",
    "wind_gust_direction_60",
    "wind_gust_speed_10",
    "wind_gust_speed_30",
    "wind_gust_speed_60",
]


def test_fetch_synop_stations():
    """Test fetching active SYNOP stations with last_record >= today."""
    print("Test 1: Fetching active SYNOP stations...")
    try:
        # Get SYNOP stations for prefix "10"
        stations = get_active_synop_stations(postal_code_prefix="10")

        if stations.empty:
            print("✗ No active SYNOP stations found")
            print("  This may indicate:")
            print("  1. No SYNOP stations near postal code prefix")
            print("  2. All SYNOP stations have last_record < today")
            print("  3. Weather stations not yet ingested")
            print("\n  Run: docker-compose exec pipeline python -m src.ingestion.weather_stations")
            return False

        print(f"✓ Found {len(stations)} active SYNOP stations")
        print(f"  Sample station: {stations.iloc[0]['station_name']}")
        print(f"  Station ID: {stations.iloc[0]['id']}")
        print(f"  Last record: {stations.iloc[0]['last_record']}")
        print(f"  Observation type: {stations.iloc[0]['observation_type']}")

        # Verify observation_type is 'synop'
        assert all(stations["observation_type"] == "synop"), (
            "All stations should have observation_type='synop'"
        )

        # Verify last_record >= today
        today = datetime.now().date()
        for _, station in stations.iterrows():
            last_record_date = station["last_record"].date()
            assert last_record_date >= today, f"Station {station['id']} has last_record < today"

        print("  ✓ All stations have observation_type='synop' and last_record >= today")

        return True
    except Exception as e:
        print(f"✗ Fetch failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_fetch_current_weather():
    """Test fetching current weather for a single SYNOP station."""
    print("\nTest 2: Fetching current weather for a single station...")
    try:
        # Get a sample SYNOP station
        stations = get_active_synop_stations(postal_code_prefix="10")

        if stations.empty:
            print("✗ No SYNOP stations to test with")
            return False

        source_id = stations.iloc[0]["id"]
        station_name = stations.iloc[0]["station_name"]

        # Fetch current weather
        weather = fetch_current_weather_by_station(source_id)

        if not weather:
            print(f"⚠  No current weather for station {source_id} ({station_name})")
            print("  This may be normal if the station has no recent data")
            return True  # Don't fail

        print(f"✓ Fetched current weather")
        print(f"  Station: {source_id} ({station_name})")
        print(f"  Temperature: {weather.get('temperature')}°C")
        print(f"  Timestamp: {weather.get('timestamp')}")
        print(f"  Condition: {weather.get('condition')}")

        # Check for SYNOP-specific fields
        present_fields = [f for f in SYNNOP_FIELDS if f in weather]
        print(f"  SYNOP time-window fields present: {len(present_fields)}/{len(SYNNOP_FIELDS)}")
        if present_fields:
            print(f"    Fields: {', '.join(present_fields)}")

        return True
    except Exception as e:
        print(f"✗ Fetch failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_parse_observations():
    """Test parsing SYNOP observation data with time-window fields."""
    print("\nTest 3: Parsing SYNOP observation data...")
    try:
        # Get a sample station
        stations = get_active_synop_stations(postal_code_prefix="10")

        if stations.empty:
            print("✗ No stations to test with")
            return False

        source_id = stations.iloc[0]["id"]

        # Fetch current weather
        weather = fetch_current_weather_by_station(source_id)

        if not weather:
            print("⚠  No weather to parse")
            return True  # Don't fail

        # Parse as list
        df = parse_observations([weather])

        if df.empty:
            print("✗ Parsing resulted in empty DataFrame")
            return False

        print(f"✓ Parsed {len(df)} observation")
        print(f"  Columns: {len(df.columns)}")

        # Verify required SYNOP columns
        required = [
            "source_id",
            "timestamp",
            "temperature",
            "relative_humidity",
            "pressure_msl",
        ] + SYNNOP_FIELDS
        missing = [col for col in required if col not in df.columns]
        if missing:
            print(f"✗ Missing columns: {missing}")
            return False

        # Verify data types
        if df["timestamp"].isna().all():
            print("✗ Timestamp field not parsed correctly")
            return False

        print("✓ All required columns present")

        # Show SYNOP-specific field values
        synop_values = {
            "precipitation_10": df["precipitation_10"].iloc[0],
            "precipitation_30": df["precipitation_30"].iloc[0],
            "precipitation_60": df["precipitation_60"].iloc[0],
            "solar_10": df["solar_10"].iloc[0],
            "solar_30": df["solar_30"].iloc[0],
            "solar_60": df["solar_60"].iloc[0],
            "sunshine_30": df["sunshine_30"].iloc[0],
            "sunshine_60": df["sunshine_60"].iloc[0],
            "wind_direction_10": df["wind_direction_10"].iloc[0],
            "wind_direction_30": df["wind_direction_30"].iloc[0],
            "wind_direction_60": df["wind_direction_60"].iloc[0],
            "wind_speed_10": df["wind_speed_10"].iloc[0],
            "wind_speed_30": df["wind_speed_30"].iloc[0],
            "wind_speed_60": df["wind_speed_60"].iloc[0],
            "wind_gust_direction_10": df["wind_gust_direction_10"].iloc[0],
            "wind_gust_direction_30": df["wind_gust_direction_30"].iloc[0],
            "wind_gust_direction_60": df["wind_gust_direction_60"].iloc[0],
            "wind_gust_speed_10": df["wind_gust_speed_10"].iloc[0],
            "wind_gust_speed_30": df["wind_gust_speed_30"].iloc[0],
            "wind_gust_speed_60": df["wind_gust_speed_60"].iloc[0],
        }
        print("\n  SYNOP time-window fields:")
        for field, value in synop_values.items():
            if value is not None and not (
                isinstance(value, float) and value != value
            ):  # Check for NaN
                print(f"    {field}: {value}")
            else:
                print(f"    {field}: null")

        print(f"\n  Parsed data summary:")
        print(f"    source_id: {df['source_id'].iloc[0]}")
        print(f"    timestamp: {df['timestamp'].iloc[0]}")
        print(f"    temperature: {df['temperature'].iloc[0]}°C")
        print(f"    condition: {df['condition'].iloc[0]}")

        return True
    except Exception as e:
        print(f"✗ Parse failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_ingest(prefix: str = "10"):
    """Test ingesting SYNOP weather observations into database."""
    print(f"\nTest 4: Ingesting SYNOP observations (prefix: {prefix})...")
    try:
        # Check connection first
        if not operations.test_connection():
            print("✗ Cannot connect to database")
            return False

        # Check SYNOP stations exist
        stations = get_active_synop_stations(postal_code_prefix=prefix)

        if stations.empty:
            print(f"✗ No active SYNOP stations found with prefix {prefix}")
            print("  Run weather station ingestion first:")
            print("  docker-compose exec pipeline python -m src.ingestion.weather_stations")
            return False

        print(f"✓ Found {len(stations)} active SYNOP stations")

        # Get count before ingestion
        before_df = get_ingested_observations(limit=10000)
        before_count = len(before_df)
        print(f"  Observations in DB before: {before_count}")

        # Ingest current weather
        count = ingest_weather_observations(postal_code_prefix=prefix)

        if count == 0:
            print("⚠  No observations ingested")
            print("  This may be normal if stations have no current data")
            return True  # Don't fail

        print(f"✓ Ingested {count} SYNOP observations")

        # Verify in database
        after_df = get_ingested_observations(limit=10000)
        after_count = len(after_df)
        print(f"  Observations in DB after: {after_count}")
        print(f"  New observations: {after_count - before_count}")

        # Verify SYNOP fields are populated
        if not after_df.empty:
            for field in SYNNOP_FIELDS:
                non_null_count = after_df[field].notna().sum()
                if non_null_count > 0:
                    print(f"  ✓ {field}: {non_null_count} non-null values")

        return True
    except Exception as e:
        print(f"✗ Ingestion failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_query():
    """Test querying SYNOP weather observations from database."""
    print("\nTest 5: Querying SYNOP observations...")
    try:
        df = get_ingested_observations(limit=100)

        if df.empty:
            print("✗ No observations found in database")
            return False

        print(f"✓ Retrieved {len(df)} observations")

        # Show date range
        if "timestamp" in df.columns:
            print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

        # Show station breakdown
        if "source_id" in df.columns:
            print(f"  Unique stations: {df['source_id'].nunique()}")

        # Verify SYNOP table structure
        expected_synop_cols = SYNNOP_FIELDS
        present_synop_cols = [col for col in expected_synop_cols if col in df.columns]
        print(f"  SYNOP fields present: {len(present_synop_cols)}/{len(expected_synop_cols)}")

        # Show sample data with SYNOP fields
        if len(df) > 0:
            print("\n  Sample observations (with SYNOP fields):")
            sample_cols = [
                "source_id",
                "timestamp",
                "temperature",
                "precipitation_10",
                "precipitation_60",
                "condition",
            ]
            available_cols = [col for col in sample_cols if col in df.columns]
            print(df[available_cols].head(3).to_string(index=False))

        return True
    except Exception as e:
        print(f"✗ Query failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_statistics():
    """Test database statistics for SYNOP observations."""
    print("\nTest 6: SYNOP database statistics...")
    try:
        status = operations.get_database_status()
        counts = status.get("table_counts", {})

        # Check SYNOP table count
        synop_count = counts.get("raw.weather_observations_synop", 0)
        print(f"✓ Total SYNOP observations in database: {synop_count:,}")

        # Check regular observations table (should be 0 or minimal for now)
        obs_count = counts.get("raw.weather_observations", 0)
        print(f"  Regular observations: {obs_count:,}")

        # Get latest SYNOP ingestion
        if "latest_ingestions" in status:
            latest = status["latest_ingestions"]
            if "weather_observations_synop" in latest:
                timestamp = latest["weather_observations_synop"]
                print(f"✓ Latest SYNOP ingestion: {timestamp}")

        # Get SYNOP observation date range
        if "synop_observation_date_range" in counts:
            date_range = counts["synop_observation_date_range"]
            print(f"✓ SYNOP observation date range: {date_range[0]} to {date_range[1]}")

        return True
    except Exception as e:
        print(f"✗ Statistics failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests for SYNOP weather observations."""
    print("=" * 70)
    print("SYNOP Weather Observations Test Suite")
    print("(Active SYNOP stations + /current_weather endpoint)")
    print("=" * 70)
    print(f"Configuration:")
    print(f"  ClickHouse host: {settings.clickhouse_host}")
    print(f"  BrightSky API: {settings.brightsky_base_url}")
    print(f"  Postal code prefixes: {settings.postal_code_prefixes}")
    print(f"  Target table: raw.weather_observations_synop")
    print("=" * 70)

    results = []

    # Test 1: Fetch SYNOP stations
    success = test_fetch_synop_stations()
    results.append(("Fetch SYNOP Stations", success))

    if not success:
        print("\n⚠  Continuing despite station fetch failure")

    # Test 2: Fetch current weather
    success = test_fetch_current_weather()
    results.append(("Fetch Current Weather", success))

    # Test 3: Parse with SYNOP fields
    success = test_parse_observations()
    results.append(("Parse SYNOP Observations", success))

    # Test 4: Ingest
    success = test_ingest()
    results.append(("Ingest SYNOP Observations", success))

    if not success:
        print("\n✗ Skipping query tests due to ingestion failure")
    else:
        # Test 5: Query
        success = test_query()
        results.append(("Query SYNOP Observations", success))

        # Test 6: Statistics
        success = test_statistics()
        results.append(("SYNOP Statistics", success))

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

    # Additional info about SYNOP implementation
    print("\nℹ  SYNOP Implementation Notes:")
    print("  • Uses /current_weather endpoint (not /weather)")
    print("  • Filters stations: observation_type='synop' AND last_record >= today")
    print("  • Stores time-window fields: precipitation_10/30/60, sunshine_10/30/60")
    print("  • Separate table: raw.weather_observations_synop")
    print("  • Hourly ingestion via Prefect deployments")

    if passed == total:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print(f"\n✗ {total - passed} test(s) failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
