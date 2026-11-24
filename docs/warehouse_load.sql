-- Warehouse load: Gold tables from the Lakehouse (LH_taxi) into the Warehouse (dbo).
-- Statements are taken from the Warehouse query history (14-15 Nov 2026), in the order they were run.
--
-- Notes:
-- * The dimensions were first created with CREATE TABLE AS SELECT (all columns nullable).
--   A primary key needs NOT NULL columns, so DimDate, DimZone, DimStation and DimFX were
--   dropped and recreated with explicit column definitions. Only the final version is shown.
-- * DimGDP, FactTaxiDaily and FactAirQualityDaily remain the CTAS versions (nullable columns, no keys).
-- * In the Warehouse, DROP, CREATE, INSERT and ALTER were run as separate queries
--   (a DROP and CREATE in the same batch did not replace the old table). Run them one at a time.

-- =====================================================================
-- 1. Dimensions
-- =====================================================================

-- DimDate
DROP TABLE IF EXISTS dbo.DimDate;

CREATE TABLE dbo.DimDate (
    date_key    INT         NOT NULL,
    [date]      DATE        NOT NULL,
    [year]      INT         NOT NULL,
    quarter     INT         NOT NULL,
    [month]     INT         NOT NULL,
    month_name  VARCHAR(20) NOT NULL,
    [day]       INT         NOT NULL,
    day_of_week INT         NOT NULL,
    day_name    VARCHAR(20) NOT NULL,
    is_weekend  BIT         NOT NULL,
    season      VARCHAR(10) NOT NULL
);

INSERT INTO dbo.DimDate
SELECT date_key, [date], [year], quarter, [month], month_name, [day],
       day_of_week, day_name, is_weekend, season
FROM LH_taxi.dbo.gold_dim_date;

-- DimZone
DROP TABLE IF EXISTS dbo.DimZone;

CREATE TABLE dbo.DimZone (
    zone_id      INT          NOT NULL,
    borough      VARCHAR(50)  NULL,
    zone_name    VARCHAR(100) NULL,
    service_zone VARCHAR(50)  NULL
);

INSERT INTO dbo.DimZone
SELECT zone_id, borough, zone_name, service_zone
FROM LH_taxi.dbo.gold_dim_zone;

-- DimStation
DROP TABLE IF EXISTS dbo.DimStation;

CREATE TABLE dbo.DimStation (
    location_id       INT          NOT NULL,
    location_name     VARCHAR(100) NULL,
    latitude          FLOAT        NULL,
    longitude         FLOAT        NULL,
    zone_id           INT          NULL,
    zone_borough      VARCHAR(50)  NULL,
    zone_name         VARCHAR(100) NULL,
    match_type        VARCHAR(20)  NULL,
    distance_km       FLOAT        NULL,
    in_nyc            BIT          NULL,
    zone_link_quality VARCHAR(20)  NULL
);

INSERT INTO dbo.DimStation
SELECT location_id, location_name, latitude, longitude, zone_id, zone_borough, zone_name,
       match_type, distance_km, in_nyc, zone_link_quality
FROM LH_taxi.dbo.gold_dim_station;

-- DimFX
DROP TABLE IF EXISTS dbo.DimFX;

CREATE TABLE dbo.DimFX (
    date_key    INT   NOT NULL,
    [date]      DATE  NOT NULL,
    usd_per_eur FLOAT NOT NULL,
    eur_per_usd FLOAT NOT NULL,
    is_filled   BIT   NOT NULL
);

INSERT INTO dbo.DimFX
SELECT date_key, [date], usd_per_eur, eur_per_usd, is_filled
FROM LH_taxi.dbo.gold_dim_fx;

-- DimGDP (CTAS)
CREATE TABLE dbo.DimGDP AS
SELECT country_code, country_name, [year], gdp_usd
FROM LH_taxi.dbo.gold_dim_gdp;

-- =====================================================================
-- 2. Primary keys (NOT ENFORCED)
-- =====================================================================
ALTER TABLE dbo.DimDate    ADD CONSTRAINT PK_DimDate    PRIMARY KEY NONCLUSTERED (date_key)    NOT ENFORCED;
ALTER TABLE dbo.DimZone    ADD CONSTRAINT PK_DimZone    PRIMARY KEY NONCLUSTERED (zone_id)     NOT ENFORCED;
ALTER TABLE dbo.DimStation ADD CONSTRAINT PK_DimStation PRIMARY KEY NONCLUSTERED (location_id) NOT ENFORCED;
ALTER TABLE dbo.DimFX      ADD CONSTRAINT PK_DimFX      PRIMARY KEY NONCLUSTERED (date_key)    NOT ENFORCED;

-- =====================================================================
-- 3. Facts
-- =====================================================================

-- FactTaxiDaily (CTAS)
CREATE TABLE dbo.FactTaxiDaily AS
SELECT CAST(FORMAT([date], 'yyyyMMdd') AS INT) AS date_key,
       pu_zone_id AS zone_id,
       trips, passengers_sum, distance_miles_sum, duration_min_sum,
       fare_usd_sum, tip_usd_sum, tolls_usd_sum, total_usd_sum
FROM LH_taxi.dbo.gold_taxi_daily;

-- FactAirQualityDaily (CTAS, 2016-2025 only)
CREATE TABLE dbo.FactAirQualityDaily AS
SELECT CAST(FORMAT([date], 'yyyyMMdd') AS INT) AS date_key,
       location_id,
       pm25_avg, no2_avg, o3_avg, co_avg, so2_avg, pm10_avg, no_avg, nox_avg
FROM LH_taxi.dbo.gold_air_quality_daily
WHERE [date] >= '2016-01-01' AND [date] <= '2025-12-31';

-- FactTaxiDaypart
DROP TABLE IF EXISTS dbo.FactTaxiDaypart;

CREATE TABLE dbo.FactTaxiDaypart (
    date_key      INT          NOT NULL,
    zone_id       INT          NOT NULL,
    daypart       VARCHAR(20)  NOT NULL,
    trips         BIGINT       NULL,
    total_usd_sum FLOAT        NULL
);

INSERT INTO dbo.FactTaxiDaypart
SELECT CAST(FORMAT([date], 'yyyyMMdd') AS INT), pu_zone_id, daypart, trips, total_usd_sum
FROM LH_taxi.dbo.gold_taxi_daypart;

-- =====================================================================
-- 4. Validation
-- =====================================================================
SELECT 'DimDate' AS tbl, COUNT(*) AS n FROM dbo.DimDate                    -- expected 3,653
UNION ALL SELECT 'DimZone', COUNT(*) FROM dbo.DimZone                      -- 265
UNION ALL SELECT 'DimStation', COUNT(*) FROM dbo.DimStation                -- 14
UNION ALL SELECT 'DimFX', COUNT(*) FROM dbo.DimFX                          -- 3,653
UNION ALL SELECT 'DimGDP', COUNT(*) FROM dbo.DimGDP                        -- 10
UNION ALL SELECT 'FactTaxiDaily', COUNT(*) FROM dbo.FactTaxiDaily          -- 822,062
UNION ALL SELECT 'FactAirQualityDaily', COUNT(*) FROM dbo.FactAirQualityDaily  -- 41,683
UNION ALL SELECT 'FactTaxiDaypart', COUNT(*) FROM dbo.FactTaxiDaypart;     -- 3,139,479

SELECT SUM(trips) AS total_trips FROM dbo.FactTaxiDaily;     -- expected 642,083,189
SELECT SUM(trips) AS total_trips FROM dbo.FactTaxiDaypart;   -- expected 642,083,189
