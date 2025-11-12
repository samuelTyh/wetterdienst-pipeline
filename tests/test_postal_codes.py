#!/usr/bin/env python3
"""Test postal code ingestion."""

import sys

from src.config import settings
from src.database import operations
from src.ingestion.postal_codes import (
    fetch_postal_codes_geojson,
    get_ingested_postal_codes,
    ingest_postal_codes,
    parse_postal_codes,
)


def test_fetch():
    """Test fetching postal codes from GitHub."""
    print("Test 1: Fetching Brotli-compressed postal codes from GitHub...")
    try:
        geojson_data = fetch_postal_codes_geojson()
        feature_count = len(geojson_data.get("features", []))
        print(f"✓ Fetched and decompressed GeoJSON with {feature_count} features")
        return True, feature_count
    except Exception as e:
        print(f"✗ Fetch failed: {e}")
        import traceback

        traceback.print_exc()
        return False, 0


def test_parse(geojson_data, prefix: str = "10"):
    """Test parsing postal codes."""
    print(f"\nTest 2: Parsing postal codes (prefix: {prefix})...")
    try:
        df = parse_postal_codes(geojson_data, prefix=prefix)
        print(f"✓ Parsed {len(df)} postal codes")
        print(f"  Columns: {list(df.columns)}")
        print(f"  Sample PLZ: {df['plz'].head(3).tolist()}")

        # Verify required columns
        required = ["plz", "note", "geometry", "centroid_lon", "centroid_lat"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            print(f"✗ Missing columns: {missing}")
            return False

        # Verify centroids are valid
        if df["centroid_lon"].isna().any() or df["centroid_lat"].isna().any():
            print("✗ Some centroids are NaN")
            return False

        print("✓ All validations passed")
        return True
    except Exception as e:
        print(f"✗ Parse failed: {e}")
        return False


def test_ingest(prefix: str = "10"):
    """Test ingesting postal codes into database."""
    print(f"\nTest 3: Ingesting postal codes (prefix: {prefix})...")
    try:
        # Check connection first
        if not operations.test_connection():
            print("✗ Cannot connect to database")
            return False

        # Ingest
        count = ingest_postal_codes(prefix=prefix)
        print(f"✓ Ingested {count} postal codes")

        # Verify in database
        df = get_ingested_postal_codes(prefix=prefix)
        db_count = len(df)
        print(f"✓ Found {db_count} postal codes in database")

        if db_count < count:
            print(f"⚠ Warning: Expected {count} but found {db_count}")

        return True
    except Exception as e:
        print(f"✗ Ingestion failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_query(prefix: str = "10"):
    """Test querying postal codes."""
    print(f"\nTest 4: Querying postal codes (prefix: {prefix})...")
    try:
        df = get_ingested_postal_codes(prefix=prefix)
        print(f"✓ Retrieved {len(df)} postal codes")

        if len(df) > 0:
            print("\nSample data:")
            print(df.head(3))

            # Verify data types
            print("\nData types:")
            print(df.dtypes)

        return True
    except Exception as e:
        print(f"✗ Query failed: {e}")
        return False


def test_statistics():
    """Test database statistics."""
    print("\nTest 5: Database statistics...")
    try:
        counts = operations.get_table_counts()
        postal_count = counts.get("raw.postal_codes", 0)
        print(f"✓ Total postal codes in database: {postal_count:,}")

        status = operations.get_database_status()
        if "latest_ingestions" in status and "postal_codes" in status["latest_ingestions"]:
            timestamp = status["latest_ingestions"]["postal_codes"]
            print(f"✓ Latest ingestion: {timestamp}")

        return True
    except Exception as e:
        print(f"✗ Statistics failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("Postal Code Ingestion Test Suite")
    print("=" * 70)
    print(f"Configuration:")
    print(f"  ClickHouse host: {settings.clickhouse_host}")
    print("=" * 70)

    results = []

    # Test 1: Fetch
    success, feature_count = test_fetch()
    results.append(("Fetch", success))

    if not success:
        print("\n✗ Skipping remaining tests due to fetch failure")
        sys.exit(1)

    # Store geojson for next test
    geojson_data = fetch_postal_codes_geojson()

    # Test 2: Parse
    success = test_parse(geojson_data)
    results.append(("Parse", success))

    # Test 3: Ingest
    success = test_ingest()
    results.append(("Ingest", success))

    if not success:
        print("\n✗ Skipping query tests due to ingestion failure")
    else:
        # Test 4: Query
        success = test_query()
        results.append(("Query", success))

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
