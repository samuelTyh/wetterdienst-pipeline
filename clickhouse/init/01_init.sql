-- Initial database schema for weather data pipeline

-- Create database if not exists (handled by environment variables in docker-compose)
CREATE DATABASE IF NOT EXISTS raw;
CREATE DATABASE IF NOT EXISTS staging;

-- Postal codes table
CREATE TABLE IF NOT EXISTS raw.postal_codes
(
    plz String,
    note String,
    geometry String,  -- Store as WKT or GeoJSON string
    centroid_lon Float64,
    centroid_lat Float64,
    ingested_at DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(ingested_at)
ORDER BY plz;

-- Weather stations table (sources from BrightSky API)
-- Complete fields from /sources and /weather endpoints
CREATE TABLE IF NOT EXISTS raw.weather_stations
(
    id UInt32,                      -- source_id from BrightSky
    dwd_station_id String,          -- DWD station identifier (e.g., "01766")
    wmo_station_id String,          -- WMO station identifier (e.g., "10315")
    station_name String,            -- Human-readable station name
    observation_type String,        -- Type: "forecast", "observation", "historical", "current", "synop"
    lat Float64,                    -- Latitude
    lon Float64,                    -- Longitude
    height Float64,                 -- Station elevation in meters
    distance Nullable(Float64),     -- Distance from query point (only when queried by lat/lon)
    first_record DateTime,          -- First available record timestamp
    last_record DateTime,           -- Last available record timestamp
    ingested_at DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(ingested_at)
ORDER BY (id, observation_type)
COMMENT 'Weather station metadata from BrightSky API /sources endpoint';

-- Weather observations raw table
-- Complete fields from /weather endpoint (observation type)
CREATE TABLE IF NOT EXISTS raw.weather_observations
(
    source_id UInt32,                       -- Reference to weather_stations.id
    timestamp DateTime,                     -- Observation timestamp
    cloud_cover Nullable(Float64),          -- Cloud cover percentage (0-100)
    condition Nullable(String),             -- Weather condition (e.g., "dry", "rain", "snow")
    dew_point Nullable(Float64),            -- Dew point in °C
    icon Nullable(String),                  -- Icon identifier (e.g., "clear-day", "rain")
    precipitation Nullable(Float64),        -- Precipitation in mm
    precipitation_probability Nullable(Float64),           -- Precipitation probability (0-100)
    precipitation_probability_6h Nullable(Float64),        -- 6h precipitation probability
    pressure_msl Nullable(Float64),         -- Mean sea level pressure in hPa
    relative_humidity Nullable(Float64),    -- Relative humidity percentage (0-100)
    sunshine Nullable(Float64),             -- Sunshine duration in minutes
    temperature Nullable(Float64),          -- Temperature in °C
    visibility Nullable(Float64),           -- Visibility in meters
    wind_direction Nullable(Float64),       -- Wind direction in degrees (0-360)
    wind_speed Nullable(Float64),           -- Wind speed in km/h
    wind_gust_direction Nullable(Float64),  -- Wind gust direction in degrees
    wind_gust_speed Nullable(Float64),      -- Wind gust speed in km/h
    ingested_at DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(ingested_at)
ORDER BY (source_id, timestamp)
COMMENT 'Raw weather observations from BrightSky API';

-- Weather forecasts raw table
-- Complete fields from /weather endpoint (forecast type)
CREATE TABLE IF NOT EXISTS raw.weather_forecasts
(
    source_id UInt32,                       -- Reference to weather_stations.id
    timestamp DateTime,                     -- Forecast timestamp (when the forecast is for)
    cloud_cover Nullable(Float64),          -- Cloud cover percentage (0-100)
    condition Nullable(String),             -- Weather condition
    dew_point Nullable(Float64),            -- Dew point in °C
    icon Nullable(String),                  -- Icon identifier
    precipitation Nullable(Float64),        -- Precipitation in mm
    precipitation_probability Nullable(Float64),           -- Precipitation probability (0-100)
    precipitation_probability_6h Nullable(Float64),        -- 6h precipitation probability
    pressure_msl Nullable(Float64),         -- Mean sea level pressure in hPa
    relative_humidity Nullable(Float64),    -- Relative humidity percentage (0-100)
    sunshine Nullable(Float64),             -- Sunshine duration in minutes
    temperature Nullable(Float64),          -- Temperature in °C
    visibility Nullable(Float64),           -- Visibility in meters
    wind_direction Nullable(Float64),       -- Wind direction in degrees (0-360)
    wind_speed Nullable(Float64),           -- Wind speed in km/h
    wind_gust_direction Nullable(Float64),  -- Wind gust direction in degrees
    wind_gust_speed Nullable(Float64),      -- Wind gust speed in km/h
    forecast_created_at DateTime,           -- When this forecast was issued
    ingested_at DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(ingested_at)
ORDER BY (source_id, timestamp, forecast_created_at)
COMMENT 'Raw weather forecasts from BrightSky API';

-- Cleaned observations per postal code (1h resolution)
CREATE TABLE IF NOT EXISTS staging.observations_by_postal_code
(
    plz String,
    timestamp DateTime,
    temperature Nullable(Float64),
    precipitation Nullable(Float64),
    relative_humidity Nullable(Float64),
    wind_speed Nullable(Float64),
    wind_direction Nullable(Float64),
    pressure_msl Nullable(Float64),
    cloud_cover Nullable(Float64),
    sunshine Nullable(Float64),
    condition Nullable(String),
    num_stations UInt32,
    data_quality_score Float64,
    is_validated Boolean,
    created_at DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(created_at)
ORDER BY (plz, timestamp);

-- Cleaned forecasts per postal code (1h resolution)
CREATE TABLE IF NOT EXISTS staging.forecasts_by_postal_code
(
    plz String,
    timestamp DateTime,
    forecast_created_at DateTime,
    temperature Nullable(Float64),
    precipitation Nullable(Float64),
    precipitation_probability Nullable(Float64),
    relative_humidity Nullable(Float64),
    wind_speed Nullable(Float64),
    wind_direction Nullable(Float64),
    pressure_msl Nullable(Float64),
    cloud_cover Nullable(Float64),
    sunshine Nullable(Float64),
    condition Nullable(String),
    num_stations UInt32,
    data_quality_score Float64,
    is_validated Boolean,
    created_at DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(created_at)
ORDER BY (plz, timestamp, forecast_created_at);

-- Create indexes for common queries
-- (ClickHouse automatically creates indexes based on ORDER BY)
