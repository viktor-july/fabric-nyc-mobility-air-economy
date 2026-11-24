# Data Dictionary

**Project:** Microsoft Fabric – Mobility (NYC Taxi) + Air Quality (OpenAQ) + Economy (GDP & FX)
**Last updated:** 22 Nov 2026
**Source of this document:** project logs (10 Nov – 18 Nov 2026) plus the RLS test of 22 Nov 2026

> **How to read this file**
> - Column lists, measures and formats were checked against the live Fabric items on 23–24 Nov 2026.

---

## 0. Environment

| Item | Name | Purpose |
|---|---|---|
| Workspace | Fabric trial workspace | Container for all items |
| Lakehouse | `LH_taxi` | Bronze, Silver and Gold-staging tables (schema `dbo`) |
| Hidden helper | `staginglakehousefordataflows` | Auto-created by Dataflow Gen2. Do not delete |
| Warehouse | `WH_Mobility_Env_Economy` | Final Gold star schema |
| Notebook | `NB_Transformations` | PySpark, `LH_taxi` is the default lakehouse |
| Pipeline | `PL_Ingestion` | Loads the 120 taxi Parquet files (manual run) |
| Dataflow Gen2 | APIs dataflow | OpenAQ, ECB FX, World Bank GDP (daily refresh) |
| Semantic model | `Mobility_Env_Economy` | Direct Lake, built on the Warehouse |
| Report | `RPT_Mobility_Env_Economy` | 4 pages |

**Naming convention:** Bronze and Silver are tables in `LH_taxi` named `bronze_*` and `silver_*`. Gold staging tables are named `gold_*`. The final star schema lives in the Warehouse (`Dim*`, `Fact*`).

**Layer overview**

| Layer | Location | Content |
|---|---|---|
| Bronze | `LH_taxi` (Files and Tables) | Raw data as ingested |
| Silver | `LH_taxi` (Tables) | Cleaned, typed, deduplicated |
| Gold (staging) | `LH_taxi` (Tables) | Aggregated, model-ready tables |
| Gold (final) | `WH_Mobility_Env_Economy` | Star schema used by Power BI |

---

## 1. Bronze layer

### 1.1 NYC Yellow Taxi trips (files)

| Property | Value |
|---|---|
| Location | `Files/Bronze/Taxi/yellow/` |
| Format | Parquet (copied as Binary, unchanged) |
| File name pattern | `yellow_tripdata_YYYY-MM.parquet` |
| Coverage | 2016-01 to 2025-12 (120 files, none missing) |
| Size | 9.76 GB |
| Source | NYC TLC trip records (CloudFront host `d37ci6vzurychx.cloudfront.net`) |
| Loaded by | `PL_Ingestion` (ForEach over a flat array of year-months, Copy activity, Binary source and sink) |
| Columns | Original TLC schema, kept unchanged. It is not uniform across years (for example `cbd_congestion_fee` exists only in 2025 files). The unified schema is defined in Silver, section 2.1 |

### 1.2 `Bronze_OpenAQ_Daily`

| Property | Value |
|---|---|
| Rows | 98,732 |
| Grain | one row per date × sensor |
| Source | OpenAQ v3 API, `/days` endpoint (daily averages) |
| Scope | 14 long-running NYC-area stations (search radius 25 km around 40.7128, -74.0060), 35 sensors, 8 parameters |

| Column | Description |
|---|---|
| `date` | Measurement day |
| `location_id` | OpenAQ station ID |
| `location_name` | Station name |
| `sensor_id` | OpenAQ sensor ID |
| `parameter` | Pollutant: pm25, pm10, no2, no, nox, o3, co, so2 |
| `value` | Daily average |
| `units` | Unit of `value` (gases in ppm, PM in µg/m³) |

Rows per parameter: pm25 30,753 · o3 19,798 · no2 14,053 · co 10,889 · so2 10,773 · no 5,242 · nox 5,242 · pm10 2,013.

### 1.3 `bronze_openaq_stations`

| Property | Value |
|---|---|
| Rows | 14 |
| Grain | one row per station |

| Column | Description |
|---|---|
| `location_id` | OpenAQ station ID (key) |
| `location_name` | Station name |
| `latitude`, `longitude` | Station coordinates |
| `locality` | Locality from the OpenAQ record |
| `country` | Country |

Station IDs: 1496, 857, 971, 1122, 628, 626, 666, 665, 648, 631, 664, 384, 625, 984.

### 1.4 `Bronze_ECB_FX`

| Property | Value |
|---|---|
| Rows | 7,197 |
| Coverage | 1999 onward |
| Meaning | USD per 1 EUR (ECB reference rate, daily, business days only) |
| Source | ECB Data API, series `EXR/D.USD.EUR.SP00.A` (CSV) |
| Columns | `KEY` (string), `CURRENCY` (string), `CURRENCY_DENOM` (string), `TIME_PERIOD` (date), `OBS_VALUE` (double, USD per EUR) |

### 1.5 `Bronze_WorldBank_GDP`

| Property | Value |
|---|---|
| Rows | 66 |
| Coverage | USA only, 1960–2025 |
| Source | World Bank API, indicator `NY.GDP.MKTP.CD` (current USD) |
| Columns | `indicator.id` (string), `indicator.value` (string), `country.id` (string), `country.value` (string), `countryiso3code` (string), `date` (date), `value` (bigint, GDP in USD), `decimal` (double, API field) |

### 1.4 Reference file `taxi_zone_lookup.csv`

| Property | Value |
|---|---|
| Location | `Files/Bronze/Taxi/reference/` |
| Rows | 265 |
| Columns | `LocationID`, `Borough`, `Zone`, `service_zone` |

> **Note on Dataflows:** each Dataflow query needs a Data destination that points to `LH_taxi`. Without it, the data goes to the hidden staging lakehouse.

---

## 2. Silver layer

### 2.1 `silver_taxi_trips`

| Property | Value |
|---|---|
| Grain | one row per cleaned trip |
| Partitioning | `pickup_year`, `pickup_month` |
| Columns | 23: 20 TLC trip columns plus 3 technical columns (`pickup_year`, `pickup_month`, `source_file`). Unified across all years. `cbd_congestion_fee` is null before 2025 |
| Rows | 642,083,189 |
| Re-runs | per month with `replaceWhere` |

**Cleaning rules**

| Rule | Condition kept |
|---|---|
| Time order | drop-off after pick-up |
| Distance | 0 to 100 miles |
| Fare and total | greater than 0 |
| Zone IDs | between 1 and 265 |
| Duration | less than 6 hours |
| Duplicates | removed |

Check on January 2016: 0.78% of rows removed.

**Trips per year (Silver)**

| Year | Trips |
|---|---|
| 2016 | 130.1M |
| 2017 | 112.5M |
| 2018 | 101.9M |
| 2019 | 83.5M |
| 2020 | 24.1M |
| 2021 | 30.3M |
| 2022 | 38.8M |
| 2023 | 37.2M |
| 2024 | 39.7M |
| 2025 | 44.2M |

### 2.2 `silver_fx_daily`

| Property | Value |
|---|---|
| Rows | 3,966 (2016-01-04 to 2026-11-12), no nulls |
| Grain | one row per calendar day |
| Gap handling | weekends and holidays are filled with the last known rate (1,184 days) |

| Column | Description |
|---|---|
| `date` | Calendar day |
| `usd_per_eur` | USD for 1 EUR |
| `eur_per_usd` | EUR for 1 USD (`1 / usd_per_eur`) |
| `is_filled` | 1 if the rate was carried forward |

### 2.3 `silver_gdp_yearly`

| Property | Value |
|---|---|
| Rows | 10 (USA, 2016–2025) |

| Column | Description |
|---|---|
| `country_code` | ISO code (USA) |
| `country_name` | Country name |
| `year` | Calendar year |
| `gdp_usd` | GDP in current USD |

### 2.4 `silver_openaq_daily`

| Property | Value |
|---|---|
| Rows | 98,718 (14 removed: negative values and duplicates) |
| Grain | one row per date × sensor |

| Column | Description |
|---|---|
| `date`, `location_id`, `location_name`, `sensor_id`, `parameter`, `value`, `units` | as in Bronze |
| `year`, `month` | derived from `date` |

Units: gases in ppm, particulate matter in µg/m³.

**Coverage caveats:** PM10 ends 2023-09. NO and NOx start 2023-03. Only PM2.5, NO2, O3, CO and SO2 cover many years.

### 2.4a `silver_taxi_zones`

| Property | Value |
|---|---|
| Rows | 265 |
| Source | `taxi_zone_lookup.csv` |
| Columns | `LocationID` (int), `Borough` (string), `Zone` (string), `service_zone` (string) |

### 2.5 `silver_station_to_zone`

| Property | Value |
|---|---|
| Rows | 14 |
| Method | spatial join (shapely) between station coordinates and NYC taxi zone polygons (NYC Open Data GeoJSON `8meu-9t5y`, 263 features, property `locationid`) |
| Columns | `location_id` (int), `location_name` (string), `latitude` (double), `longitude` (double), `zone_id` (int), `match_type` (string, exact or nearest), `distance_km` (double), `Borough`, `Zone`, `service_zone` (string) |

| Link type | Stations |
|---|---|
| Exact (station lies inside a zone) | 9: Bronx IS52 (147), Pfizer Lab (31), Manhattan/IS143 (243), Maspeth (157), Bklyn PS274 (37), CCNY (152), Bronx IS74 (126), Bklyn PS314 (228), Queens (135) |
| Nearest (approximate, all in New Jersey) | 5: Fort Lee, Elizabeth, Leonia, Jersey City, Bayonne. Example: Jersey City snapped to Governor's Island |

---

## 3. Gold layer – staging tables in `LH_taxi`

| Table | Rows | Grain | Notes |
|---|---|---|---|
| `gold_taxi_daily` | 822,062 | date × pickup zone | Partitioned by `pickup_year`, `pickup_month`. Stores **sums only**. Averages are computed as SUM / SUM |
| `gold_taxi_daypart` | not logged | date × zone × daypart | Five dayparts, see below |
| `gold_air_quality_daily` | 45,988 | date × station | Pivoted: one column per pollutant. Range 2016-03-06 to 2026-11-10. 4,305 rows from 2026 are not loaded into the Warehouse |
| `gold_dim_date` | 3,653 | day | 2016-01-01 to 2025-12-31 |
| `gold_dim_zone` | 265 | taxi zone | |
| `gold_dim_station` | 14 | station | Adds `in_nyc` and `zone_link_quality` |
| `gold_dim_fx` | 3,653 | day | 1–3 Jan 2016 use the last 2015 ECB rate (1.0887, `is_filled` = true) |
| `gold_dim_gdp` | 10 | year | USA, 2016–2025 |

**Dayparts**

| Daypart | Hours | Length |
|---|---|---|
| `1_overnight` | 00–06 | 6 h |
| `2_morning_rush` | 06–10 | 4 h |
| `3_midday` | 10–16 | 6 h |
| `4_evening_rush` | 16–20 | 4 h |
| `5_night` | 20–24 | 4 h |

Dayparts have different lengths, so bars are not comparable per hour.

**Validation:** yearly trip totals in `gold_taxi_daily` and `gold_taxi_daypart` match Silver exactly (total 642,083,189). Taxi dates missing in `DimDate` = 0. Taxi zones missing in `DimZone` = 0. Air quality stations missing in `DimStation` = 0.

---

## 4. Warehouse – `WH_Mobility_Env_Economy` (schema `dbo`)

The Warehouse reads the Lakehouse by three-part name (`LH_taxi.dbo.<table>`).

### 4.1 Dimensions

**`DimDate`** (3,653 rows, PK `date_key`)

| Column | Description |
|---|---|
| `date_key` | Integer key (number) |
| `date` | Calendar date |
| `year`, `quarter`, `month`, `month_name`, `day` | Date parts |
| `day_of_week`, `day_name` | Weekday number and name |
| `is_weekend` | Weekend flag |
| `season` | Season |

**`DimZone`** (265 rows, PK `zone_id`)

| Column | Description |
|---|---|
| `zone_id` | TLC LocationID |
| `borough` | Borough (used by RLS role `Borough_Manhattan`) |
| `zone_name` | Zone name |
| `service_zone` | TLC service zone |

**`DimStation`** (14 rows, PK `location_id`)

| Column | Description |
|---|---|
| `location_id` | OpenAQ station ID |
| `location_name` | Station name |
| `latitude`, `longitude` | Station coordinates, from `bronze_openaq_stations` |
| `zone_id` | TLC zone the station was mapped to (from `silver_station_to_zone`) |
| `zone_borough`, `zone_name` | Borough and name of that zone |
| `match_type` | `exact` (station inside the zone) or `nearest` |
| `distance_km` | Distance to the zone used for `nearest` matches |
| `in_nyc` | bit: 1 for the 9 stations inside a NYC zone (used by RLS role `NYC_Stations_Only`) |
| `zone_link_quality` | `exact` or `approximate` |

> `DimStation` stores the mapped zone, but there is deliberately no relationship to `DimZone` in the semantic model: the 5 NJ stations are snapped to the nearest NYC zone (for example Jersey City to Governor's Island) and would create ambiguity.

**`DimFX`** (3,653 rows, PK `date_key`)

| Column | Description |
|---|---|
| `date_key`, `date` | Day |
| `usd_per_eur` | USD for 1 EUR |
| `eur_per_usd` | EUR for 1 USD |
| `is_filled` | 1 if carried forward |

**`DimGDP`** (10 rows, no PK)

| Column | Description |
|---|---|
| `country_code`, `country_name` | USA |
| `year` | Year |
| `gdp_usd` | GDP in current USD |

### 4.2 Facts

**`FactTaxiDaily`** (822,062 rows, grain: date × pickup zone)

| Column | Description |
|---|---|
| `date_key` | FK to `DimDate` |
| `zone_id` | FK to `DimZone` (pickup zone) |
| `trips` | Number of trips |
| `passengers_sum` | Sum of passengers |
| `distance_miles_sum` | Sum of distance |
| `duration_min_sum` | Sum of trip duration in minutes |
| `fare_usd_sum` | Sum of fare |
| `tip_usd_sum` | Sum of tips |
| `tolls_usd_sum` | Sum of tolls |
| `total_usd_sum` | Sum of total amount |

Zone-days with zero pickups have no row.

**`FactTaxiDaypart`** (3,139,479 rows, grain: date × zone × daypart)

| Column | Description |
|---|---|
| `date_key`, `zone_id` | FKs |
| `daypart` | One of the five dayparts |
| `trips` | Number of trips |
| `total_usd_sum` | Sum of total amount |

**`FactAirQualityDaily`** (41,683 rows, 2016–2025 only, grain: date × station)

| Column | Description |
|---|---|
| `date_key` | FK to `DimDate` |
| `location_id` | FK to `DimStation` |
| `pm25_avg`, `pm10_avg` | µg/m³ |
| `no2_avg`, `o3_avg`, `co_avg`, `so2_avg`, `no_avg`, `nox_avg` | ppm |

**Station coverage facts (days with data)**

| Pollutant | Coverage |
|---|---|
| PM2.5 | 8 NYC stations. Pfizer Lab has 0 PM2.5 days. Jersey City and Bayonne have none |
| NO2 | **No NYC station.** Only NJ: Bayonne 3,403 · Elizabeth 3,373 · Fort Lee 3,364 · Jersey City 2,666 · Leonia 0 |
| O3 | 4 NYC stations (Bronx IS52, CCNY, Pfizer Lab, Queens) plus Bayonne and Leonia |

### 4.3 Warehouse notes

- Primary keys are **NOT ENFORCED** (metadata only).
- Fact tables and `DimGDP` are CTAS versions, so their columns are nullable.
- Run `DROP`, `CREATE`, `INSERT` and `ALTER` as separate queries. A `DROP` and `CREATE` in one batch did not replace the table.
- Total check: `SUM(trips)` in both taxi facts = 642,083,189.

---

## 5. Semantic model – `Mobility_Env_Economy`

| Setting | Value |
|---|---|
| Storage mode | Direct Lake |
| Large semantic model storage format | On |
| OneLake integration | Off |
| Date table | `DimDate[date]` |
| "Keep your Direct Lake data up to date" | On |

### 5.1 Relationships (all single direction, active)

| From (one) | To (many) | Cardinality |
|---|---|---|
| `DimDate[date_key]` | `FactTaxiDaily[date_key]` | 1:* |
| `DimDate[date_key]` | `FactTaxiDaypart[date_key]` | 1:* |
| `DimDate[date_key]` | `FactAirQualityDaily[date_key]` | 1:* |
| `DimZone[zone_id]` | `FactTaxiDaily[zone_id]` | 1:* |
| `DimZone[zone_id]` | `FactTaxiDaypart[zone_id]` | 1:* |
| `DimStation[location_id]` | `FactAirQualityDaily[location_id]` | 1:* |
| `DimDate[date_key]` | `DimFX[date_key]` | 1:1 |

**Deliberately no relationship:**
- `DimGDP`: `year` is not unique in `DimDate`, so a `TREATAS` measure is used.
- `DimStation` ↔ `DimZone`: the NJ stations are snapped to the nearest zone and would create ambiguity.

### 5.2 Measures

| Measure | Table | Definition | Format | Notes |
|---|---|---|---|---|
| `Total Trips` | FactTaxiDaily | `SUM(FactTaxiDaily[trips])` | `#,0` | Cannot be named "Trips" (clashes with the column) |
| `Revenue USD` | FactTaxiDaily | `SUM(FactTaxiDaily[total_usd_sum])` | `$#,0.00` |  |
| `Avg Revenue per Trip USD` | FactTaxiDaily | `DIVIDE([Revenue USD], [Total Trips])` | `$#,0.00` |  |
| `Revenue EUR` | FactTaxiDaily | `SUMX(VALUES(DimDate[date_key]), [Revenue USD] * CALCULATE(MAX(DimFX[eur_per_usd])))` | `€ #,0.00` | Daily rate × daily revenue. The `CALCULATE` is required; without it every day used the year's highest rate |
| `Avg Revenue per Trip EUR` | FactTaxiDaily | `DIVIDE([Revenue EUR], [Total Trips])` | `€ #,0.00` |  |
| `Avg PM2.5 NYC` | FactTaxiDaily | `CALCULATE(AVERAGE(FactAirQualityDaily[pm25_avg]), DimStation[in_nyc] = TRUE())` | `0.00` | 8 stations |
| `Avg NO2 NYC` | FactTaxiDaily | same pattern with `no2_avg` | none (blank by design) | Blank by design (no NYC NO2 data) |
| `Avg NO2 NYC ppb` | FactAirQualityDaily | `[Avg NO2 NYC] * 1000` | none (blank by design) | Blank by design |
| `Avg O3 NYC ppb` | FactAirQualityDaily | `CALCULATE(AVERAGE(FactAirQualityDaily[o3_avg]), DimStation[in_nyc] = TRUE()) * 1000` | `0.0` | 4 stations |
| `Avg NO2 Jersey City ppb` | FactAirQualityDaily | `CALCULATE(AVERAGE(FactAirQualityDaily[no2_avg]), DimStation[location_name] = "Jersey City") * 1000` | `0.0` | NJ regional proxy, not NYC |
| `Avg PM2.5` | FactAirQualityDaily | `AVERAGE(FactAirQualityDaily[pm25_avg])` | `0.00` | All 14 stations |
| `Avg NO2 ppb` | FactAirQualityDaily | `AVERAGE(FactAirQualityDaily[no2_avg]) * 1000` | `0.0` |  |
| `Daypart Trips` | FactTaxiDaypart | `SUM(FactTaxiDaypart[trips])` | `#,0` |  |
| `GDP USD tn` | FactTaxiDaily | `VAR y = MAX(DimDate[year]) RETURN CALCULATE(SUM(DimGDP[gdp_usd]) / 1e12, TREATAS({y}, DimGDP[year]))` | `0.00` |  |

The optional measures from earlier logs (`Trips Top 10 Zones`, `Trips 7d Avg`, `Zone Rank`) do not exist in the model and are not part of this project. Home tables were read from the model view on 23 Nov 2026. Formats were read from the model with `EVALUATE INFO.VIEW.MEASURES()` (DAX query view) and are listed in the Format column. They are set in the semantic model under Properties → Formatting.

### 5.3 Row-level security

| Role | Table | Filter | Test result |
|---|---|---|---|
| `Borough_Manhattan` | `DimZone` | `[borough] = "Manhattan"` | Total Trips 579,967,984, equal to the SQL check on the Warehouse (90.3% of 642,083,189) |
| `NYC_Stations_Only` | `DimStation` | `[in_nyc] = TRUE()` | NJ-only NO2 chart goes blank. `Avg PM2.5 NYC` for 2025 = 7.75, same as without the role |

Tested with "Test as role" in the Power BI service. The first attempt failed with an SSO error and worked after signing in again with fresh credentials. Members are assigned in the model's Security menu. No members are assigned in this trial workspace (single account), so both roles exist and were tested with "Test as role" only.

---

## 6. Report – `RPT_Mobility_Env_Economy`

| Page | Content |
|---|---|
| Mobility | Year slicer, cards (trips, revenue, avg revenue per trip), daily trips line, top zones bar, daypart columns, avg fare by year |
| Air Quality | Year slicer, PM2.5 NYC (8 stations), O3 NYC (4 stations), NO2 Jersey City (NJ proxy), caveat text box |
| Mobility vs Air Quality | Scatter of daily trips vs PM2.5 NYC, combo chart by year, finding text box |
| Economic Impact | Avg revenue per trip USD vs EUR, Revenue USD vs GDP, EUR per USD daily line, text box |
