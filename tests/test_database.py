#!/usr/bin/env python3
"""Test script for ClickHouse database operations."""

import sys
from datetime import datetime

from src.database import operations
from src.database.clickhouse_client import get_client
from src.database.schema import PostalCode, WeatherStation


def test_connection():
    """Test basic database connection."""
    print("Testing database connection...")
    if operations.test_connection():
        print("✓ Connection successful")
        return True
    else:
        print("✗ Connection failed")
        return False


def test_databases_exist():
    """Test that required databases exist."""
    print("\nChecking databases...")
    client = get_client()

    databases = ["raw", "staging"]
    for db in databases:
        try:
            result = client.execute(f"EXISTS DATABASE {db}")
            if result.result_rows[0][0] == 1:
                print(f"✓ Database '{db}' exists")
            else:
                print(f"✗ Database '{db}' does not exist")
                return False
        except Exception as e:
            print(f"✗ Error checking database '{db}': {e}")
            return False

    return True


def test_tables_exist():
    """Test that required tables exist."""
    print("\nChecking tables...")
    client = get_client()

    tables = [
        "raw.postal_codes",
        "raw.weather_stations",
        "raw.weather_observations",
        "raw.weather_forecasts",
        "staging.observations_by_postal_code",
        "staging.forecasts_by_postal_code",
    ]

    for table in tables:
        try:
            result = client.execute(f"EXISTS TABLE {table}")
            if result.result_rows[0][0] == 1:
                print(f"✓ Table '{table}' exists")
            else:
                print(f"✗ Table '{table}' does not exist")
                return False
        except Exception as e:
            print(f"✗ Error checking table '{table}': {e}")
            return False

    return True


def test_table_structure():
    """Test table structure."""
    print("\nChecking table structures...")
    client = get_client()

    # Check postal_codes table
    try:
        result = client.execute("DESCRIBE TABLE raw.postal_codes")
        columns = [row[0] for row in result.result_rows]
        expected = ["plz", "note", "geometry", "centroid_lon", "centroid_lat", "ingested_at"]
        if all(col in columns for col in expected):
            print("✓ Table 'raw.postal_codes' has correct structure")
        else:
            print("✗ Table 'raw.postal_codes' has incorrect structure")
            print(f"  Expected: {expected}")
            print(f"  Found: {columns}")
            return False
    except Exception as e:
        print(f"✗ Error checking table structure: {e}")
        return False

    return True


def test_insert_operations():
    """Test insert operations."""
    print("\nTesting insert operations...")

    # Test postal code insert
    try:
        test_postal_code = PostalCode(
            plz="99999",
            note="Test postal code",
            geometry="POINT(13.4 52.5)",
            centroid_lon=13.4,
            centroid_lat=52.5,
        )
        operations.insert_postal_codes([test_postal_code])
        print("✓ Postal code insert successful")

        # Verify insert
        client = get_client()
        result = client.execute("SELECT count() FROM raw.postal_codes WHERE plz = '99999'")
        count = result.result_rows[0][0]
        if count > 0:
            print(f"✓ Postal code found in database (count: {count})")
        else:
            print("✗ Postal code not found after insert")
            return False

    except Exception as e:
        print(f"✗ Postal code insert failed: {e}")
        return False

    # Test weather station insert
    try:
        test_station = WeatherStation(
            id=999999,
            dwd_station_id="99999",
            wmo_station_id="99999",
            station_name="Test Station",
            observation_type="test",
            lat=52.5,
            lon=13.4,
            height=100.0,
            distance=None,
            first_record=datetime.now(),
            last_record=datetime.now(),
        )
        operations.insert_weather_stations([test_station])
        print("✓ Weather station insert successful")

        # Verify insert
        client = get_client()
        result = client.execute("SELECT count() FROM raw.weather_stations WHERE id = 999999")
        count = result.result_rows[0][0]
        if count > 0:
            print(f"✓ Weather station found in database (count: {count})")
        else:
            print("✗ Weather station not found after insert")
            return False

    except Exception as e:
        print(f"✗ Weather station insert failed: {e}")
        return False

    return True


def test_query_operations():
    """Test query operations."""
    print("\nTesting query operations...")

    try:
        # Test get_postal_codes
        df = operations.get_postal_codes()
        print(f"✓ Retrieved {len(df)} postal codes")

        # Test get_weather_stations
        df = operations.get_weather_stations()
        print(f"✓ Retrieved {len(df)} weather stations")

        # Test get_table_counts
        counts = operations.get_table_counts()
        print("✓ Table counts:")
        for table, count in counts.items():
            print(f"  - {table}: {count:,} rows")

        # Test get_database_status
        status = operations.get_database_status()
        print(f"✓ Database status retrieved: {status}")

    except Exception as e:
        print(f"✗ Query operations failed: {e}")
        return False

    return True


def cleanup_test_data():
    """Clean up test data."""
    print("\nCleaning up test data...")
    client = get_client()

    try:
        client.command("DELETE FROM raw.postal_codes WHERE plz = '99999'")
        client.command("DELETE FROM raw.weather_stations WHERE id = 999999")
        print("✓ Test data cleaned up")
    except Exception as e:
        print(f"⚠ Cleanup warning: {e}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("ClickHouse Database Operations Test Suite")
    print("=" * 60)

    tests = [
        ("Connection", test_connection),
        ("Databases", test_databases_exist),
        ("Tables", test_tables_exist),
        ("Table Structure", test_table_structure),
        ("Insert Operations", test_insert_operations),
        ("Query Operations", test_query_operations),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' failed with exception: {e}")
            results.append((name, False))

    # Cleanup
    cleanup_test_data()

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    # Exit with appropriate code
    if passed == total:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print(f"\n✗ {total - passed} test(s) failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
