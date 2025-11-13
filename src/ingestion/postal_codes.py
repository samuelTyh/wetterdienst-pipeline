"""Postal code data ingestion from GitHub repository."""

import json
from typing import Any

import brotli
import geopandas as gpd
import httpx
import pandas as pd
from shapely.geometry import shape

from src.config import settings
from src.database import operations

# GitHub repository URL for German postal codes (Brotli-compressed)
POSTAL_CODES_URL = (
    "https://github.com/yetzt/postleitzahlen/releases/download/2024.12/postleitzahlen.geojson.br"
)


def fetch_postal_codes_geojson() -> dict[str, Any]:
    """Fetch postal code GeoJSON from GitHub.

    The file is Brotli-compressed (.br), so we need to decompress it.

    Returns:
        GeoJSON data as dictionary

    Raises:
        httpx.HTTPError: If request fails
    """
    print(f"Downloading from: {POSTAL_CODES_URL}")
    response = httpx.get(POSTAL_CODES_URL, timeout=60.0, follow_redirects=True)
    response.raise_for_status()

    print("Decompressing Brotli data...")
    # Decompress Brotli-compressed data
    decompressed_data = brotli.decompress(response.content)

    # Parse JSON
    geojson_data = json.loads(decompressed_data)
    print(f"Loaded {len(geojson_data.get('features', []))} postal codes")

    return geojson_data


def parse_postal_codes(geojson_data: dict[str, Any], prefix: str | None = None) -> pd.DataFrame:
    """Parse GeoJSON data into DataFrame.

    Args:
        geojson_data: GeoJSON data from API
        prefix: Optional postal code prefix to filter (e.g., "10" for Berlin)

    Returns:
        DataFrame with postal code data
    """
    # Convert to GeoDataFrame
    gdf = gpd.GeoDataFrame.from_features(geojson_data["features"])

    # Ensure CRS is set, fallback to EPSG:4326 if missing
    if gdf.crs is None:
        gdf.set_crs(epsg=4326, inplace=True)

    # Extract postcode from properties (new format uses 'postcode' field)
    if "postcode" in gdf.columns:
        gdf["plz"] = gdf["postcode"]
    elif "properties" in gdf.columns:
        # Handle nested properties if needed
        gdf["plz"] = gdf["properties"].apply(lambda x: x.get("postcode", ""))

    # Filter out any empty postal codes
    gdf = gdf[gdf["plz"].notna() & (gdf["plz"] != "")]

    # Filter by prefix if provided
    if prefix:
        gdf = gdf[gdf["plz"].str.startswith(prefix)]

    # Calculate centroids using Equal Area Cylindrical projection
    cea_gdf = gdf.to_crs("+proj=cea")
    centroids = cea_gdf.centroid.to_crs(gdf.crs)

    gdf["centroid_lon"] = centroids.x
    gdf["centroid_lat"] = centroids.y

    # Convert geometry to GeoJSON string for storage
    gdf["geometry_str"] = gdf.geometry.apply(lambda geom: json.dumps(geom.__geo_interface__))

    # Create DataFrame with required columns
    df = pd.DataFrame(
        {
            "plz": gdf["plz"],
            "note": "",  # No note field in new format, use empty string
            "geometry": gdf["geometry_str"],
            "centroid_lon": gdf["centroid_lon"],
            "centroid_lat": gdf["centroid_lat"],
        }
    )

    # Reset index to avoid issues
    df = df.reset_index(drop=True)

    print(f"Parsed {len(df)} postal codes from {len(geojson_data.get('features', []))} features")

    return df


def ingest_postal_codes(prefix: str | None = None) -> int:
    """Ingest postal codes into database.

    Args:
        prefix: Optional postal code prefix to filter (e.g., "10" for Berlin)

    Returns:
        Number of postal codes ingested
    """
    # Fetch data
    print(f"Fetching postal codes from {POSTAL_CODES_URL}...")
    geojson_data = fetch_postal_codes_geojson()

    # Parse data
    print(f"Parsing postal codes (prefix: {prefix or 'all'})...")
    df = parse_postal_codes(geojson_data, prefix=prefix)

    # Insert into database
    print(f"Inserting {len(df)} postal codes into database...")
    operations.insert_postal_codes_df(df)

    print(f"✓ Successfully ingested {len(df)} postal codes")
    return len(df)


def get_ingested_postal_codes(prefix: str | None = None) -> pd.DataFrame:
    """Get postal codes from database.

    Args:
        prefix: Optional postal code prefix to filter

    Returns:
        DataFrame with postal code data
    """
    return operations.get_postal_codes(prefix=prefix)


if __name__ == "__main__":
    # Run ingestion with all postal codes

    count = ingest_postal_codes()
    print(f"\nIngested {count} postal codes")

    df = get_ingested_postal_codes()
    print(f"\nSample of {len(df)} postal codes:")
    print(df.head())
