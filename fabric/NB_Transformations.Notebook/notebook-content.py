# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "175b3837-9b91-4dde-b912-ced02782891b",
# META       "default_lakehouse_name": "LH_Taxi",
# META       "default_lakehouse_workspace_id": "ddd76090-4451-4a74-80b1-5e6c6747ef20",
# META       "known_lakehouses": [
# META         {
# META           "id": "175b3837-9b91-4dde-b912-ced02782891b"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

import requests
import pandas as pd

API_KEY = "OPENAQ_API_KEY"

url = "https://api.openaq.org/v3/locations"
params = {
    "coordinates": "40.7128,-74.0060",
    "radius": 25000,
    "limit": 1000,
    "page": 1
}
headers = {
    "X-API-Key": API_KEY
}

response = requests.get(url, params=params, headers=headers)

if response.status_code == 200:
    data = response.json()
    results = data.get("results", [])
    
    df = pd.json_normalize(results)
    
    print(f"Number of locations found: {len(df)}")
    display(df[["id", "name", "locality", "datetimeFirst.utc", "datetimeLast.utc"]].head(20))

else:
    print("Error:", response.status_code, response.text)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

df_clean = df[["id", "name", "locality", "datetimeFirst.utc", "datetimeLast.utc", "isMonitor"]].copy()

df_clean["datetimeFirst.utc"] = pd.to_datetime(df_clean["datetimeFirst.utc"])
df_clean["datetimeLast.utc"] = pd.to_datetime(df_clean["datetimeLast.utc"])

df_clean["years_active"] = (df_clean["datetimeLast.utc"] - df_clean["datetimeFirst.utc"]).dt.days / 365.25

df_proper = df_clean[
    (df_clean["datetimeLast.utc"] >= "2025-01-01") &
    (df_clean["years_active"] >= 10)
].sort_values("years_active", ascending=False)

print(f"Total locations found: {len(df)}")
print(f"Proper long-running locations (active + ≥3 years): {len(df_proper)}")
print()
display(df_proper)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

location_ids = [1496, 857, 971, 1122, 628, 626, 666, 665, 648, 631, 664, 384, 625, 984]

all_sensors = []

for loc_id in location_ids:
    url = f"https://api.openaq.org/v3/locations/{loc_id}/sensors"
    headers = {"X-API-Key": API_KEY}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        sensors = data.get("results", [])
        
        for s in sensors:
            all_sensors.append({
                "location_id": loc_id,
                "sensor_id": s.get("id"),
                "sensor_name": s.get("name"),
                "parameter": s.get("parameter", {}).get("name"),
                "units": s.get("parameter", {}).get("units"),
                "display_name": s.get("parameter", {}).get("displayName")
            })
    else:
        print(f"Failed for location {loc_id}: {response.status_code}")

df_sensors = pd.DataFrame(all_sensors)

print(f"Total sensors found: {len(df_sensors)}")
print()
display(df_sensors.sort_values(["location_id", "parameter"]))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

target_sensors = [
    # PM2.5
    673, 1097, 1102, 1103, 1152, 1128, 1145, 1146, 1534, 1758,
    # NO2
    1535, 3951, 23341, 2644,
    # NO
    4272431, 4272273, 4272352, 4272224,
    # NOx
    4272250, 4272290, 4272080, 4272086,
    # PM10
    1099,
    # CO
    1536, 3952, 2016,
    # O3
    671, 1098, 1106, 1147, 1777, 2645,
    # SO2
    3950, 2018, 2646
]

all_measurements = []

for sensor_id in target_sensors:
    print(f"Loading sensor {sensor_id}...")
    
    page = 1
    while True:
        url = f"https://api.openaq.org/v3/sensors/{sensor_id}/days"
        params = {
            "limit": 1000,
            "page": page
        }
        headers = {"X-API-Key": API_KEY}
        
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code != 200:
            print(f"  → Error on sensor {sensor_id}, page {page}: {response.status_code}")
            break
            
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            break
            
        for r in results:
            all_measurements.append({
                "sensor_id": sensor_id,
                "value": r.get("value"),
                "parameter": r.get("parameter", {}).get("name"),
                "units": r.get("parameter", {}).get("units"),
                "datetime_from": r.get("period", {}).get("datetimeFrom", {}).get("utc"),
                "datetime_to": r.get("period", {}).get("datetimeTo", {}).get("utc")
            })
        
        if len(results) < 1000:
            break
            
        page += 1

df_meas = pd.DataFrame(all_measurements)

print(f"\n=== DONE ===")
print(f"Total daily measurements loaded: {len(df_meas):,}")
print("\nBreakdown by parameter:")
print(df_meas["parameter"].value_counts())

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

df_meas["datetime_from"] = pd.to_datetime(df_meas["datetime_from"])
df_meas["datetime_to"] = pd.to_datetime(df_meas["datetime_to"])
df_meas["date"] = df_meas["datetime_from"].dt.date

df_meas = df_meas.dropna(subset=["value", "datetime_from"])

sensor_to_location = {
    673: 384, 1097: 625, 1102: 626, 1103: 628, 1152: 631,
    1128: 648, 1145: 664, 1146: 665, 1534: 857, 1758: 971,
    1535: 857, 3951: 971, 23341: 1122, 2644: 1496,
    4272431: 857, 4272273: 971, 4272352: 1122, 4272224: 1496,
    4272250: 857, 4272290: 971, 4272080: 1122, 4272086: 1496,
    1099: 626,
    1536: 857, 3952: 971, 2016: 1122,
    671: 384, 1098: 626, 1106: 631, 1147: 666, 1777: 984, 2645: 1496,
    3950: 971, 2018: 1122, 2646: 1496
}

df_meas["location_id"] = df_meas["sensor_id"].map(sensor_to_location)

location_names = {
    384: "CCNY", 625: "Manhattan/IS143", 626: "Bronx - IS52",
    628: "Maspeth", 631: "Queens", 648: "Bklyn - PS 314",
    664: "Bklyn - PS274", 665: "Bronx - IS74", 666: "Pfizer Lab",
    857: "Fort Lee Near Road", 971: "Elizabeth Trailer",
    984: "Leonia", 1122: "Jersey City", 1496: "Bayonne"
}

df_meas["location_name"] = df_meas["location_id"].map(location_names)

df_final = df_meas[[
    "date", "location_id", "location_name", "sensor_id",
    "parameter", "value", "units", "datetime_from", "datetime_to"
]].sort_values(["date", "location_id", "parameter"])

print("Final shape:", df_final.shape)
print("\nSample:")
display(df_final.head(10))

spark_df = spark.createDataFrame(df_final)
spark_df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("Bronze_OpenAQ_Daily")

print("\nSuccessfully written to Lakehouse table: Bronze_OpenAQ_Daily")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

spark_df = spark.createDataFrame(df_final)

spark_df.write.mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable("Bronze_OpenAQ_Daily")

print("Successfully written to Lakehouse table: Bronze_OpenAQ_Daily")
print(f"Rows written: {spark_df.count():,}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

files = [f for f in notebookutils.fs.ls("Files/Bronze/Taxi/yellow") if f.name.endswith(".parquet")]
print(len(files), "files")
print(round(sum(f.size for f in files)/1e9, 2), "GB")
expected = {f"yellow_tripdata_{y}-{m:02d}.parquet" for y in range(2016, 2026) for m in range(1, 13)}
print("Missing:", sorted(expected - {f.name for f in files}))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

for t in ["Bronze_OpenAQ_Daily", "Bronze_ECB_FX", "Bronze_WorldBank_GDP"]:
    try:
        df = spark.table(t)
        print(t, "-", df.count(), "rows")
        df.printSchema()
        df.show(3, truncate=False)
    except Exception as e:
        print(t, "- ERROR:", str(e)[:200])

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

spark.sql("DROP TABLE IF EXISTS silver_taxi_trips")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F
import re

BASE = "Files/Bronze/Taxi/yellow"
TARGET = "silver_taxi_trips"

schema_map = {
    "vendorid": "int", "tpep_pickup_datetime": "timestamp", "tpep_dropoff_datetime": "timestamp",
    "passenger_count": "int", "trip_distance": "double", "ratecodeid": "int",
    "store_and_fwd_flag": "string", "pulocationid": "int", "dolocationid": "int",
    "payment_type": "int", "fare_amount": "double", "extra": "double", "mta_tax": "double",
    "tip_amount": "double", "tolls_amount": "double", "improvement_surcharge": "double",
    "total_amount": "double", "congestion_surcharge": "double", "airport_fee": "double",
    "cbd_congestion_fee": "double",
}

def load_month(path, year, month):
    df = spark.read.parquet(path)
    df = df.toDF(*[c.lower() for c in df.columns])
    cols = [F.col(n).cast(t).alias(n) if n in df.columns else F.lit(None).cast(t).alias(n)
            for n, t in schema_map.items()]
    df = df.select(*cols)
    df = (df.withColumn("pickup_year", F.year("tpep_pickup_datetime"))
            .withColumn("pickup_month", F.month("tpep_pickup_datetime"))
            .withColumn("source_file", F.lit(path.split("/")[-1])))
    df = df.filter((F.col("pickup_year") == year) & (F.col("pickup_month") == month))
    df = df.filter(
        (F.col("tpep_dropoff_datetime") > F.col("tpep_pickup_datetime")) &
        (F.col("trip_distance") > 0) & (F.col("trip_distance") < 100) &
        (F.col("fare_amount") > 0) & (F.col("total_amount") > 0) &
        F.col("pulocationid").between(1, 265) & F.col("dolocationid").between(1, 265) &
        ((F.unix_timestamp("tpep_dropoff_datetime") - F.unix_timestamp("tpep_pickup_datetime")) < 6*3600)
    )
    return df.dropDuplicates()

files = sorted((f.path, f.name) for f in notebookutils.fs.ls(BASE) if f.name.endswith(".parquet"))

for p, name in files:
    y, m = map(int, re.search(r"(\d{4})-(\d{2})", name).groups())
    out = load_month(p, y, m)
    w = out.write.format("delta").partitionBy("pickup_year", "pickup_month")
    if not spark.catalog.tableExists(TARGET):
        w.mode("overwrite").saveAsTable(TARGET)
    else:
        w.mode("overwrite").option("replaceWhere", f"pickup_year = {y} AND pickup_month = {m}").saveAsTable(TARGET)
    print("done", y, m)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

spark.sql("SELECT pickup_year, COUNT(*) trips FROM silver_taxi_trips GROUP BY 1 ORDER BY 1").show(20)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F, Window

fx = (spark.table("Bronze_ECB_FX")
      .filter(F.col("TIME_PERIOD") >= "2016-01-01")
      .select(F.col("TIME_PERIOD").alias("date"), F.col("OBS_VALUE").alias("usd_per_eur"))
      .dropDuplicates(["date"]))

mn, mx = fx.agg(F.min("date"), F.max("date")).first()
cal = spark.sql(f"SELECT explode(sequence(to_date('{mn}'), to_date('{mx}'), interval 1 day)) AS date")

w = Window.orderBy("date").rowsBetween(Window.unboundedPreceding, 0)
silver_fx = (cal.join(fx, "date", "left")
             .withColumn("is_filled", F.col("usd_per_eur").isNull())
             .withColumn("usd_per_eur", F.last("usd_per_eur", ignorenulls=True).over(w))
             .withColumn("eur_per_usd", F.round(1 / F.col("usd_per_eur"), 6)))

silver_fx.write.format("delta").mode("overwrite").saveAsTable("silver_fx_daily")

spark.sql("""SELECT MIN(date) first_day, MAX(date) last_day, COUNT(*) days,
             SUM(CASE WHEN is_filled THEN 1 ELSE 0 END) filled_days,
             SUM(CASE WHEN usd_per_eur IS NULL THEN 1 ELSE 0 END) null_rates
             FROM silver_fx_daily""").show()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F

gdp = (spark.table("Bronze_WorldBank_GDP")
       .select(
           F.col("`countryiso3code`").alias("country_code"),
           F.col("`country.value`").alias("country_name"),
           F.year("date").alias("year"),
           F.col("value").cast("double").alias("gdp_usd"))
       .filter(F.col("gdp_usd").isNotNull())
       .filter(F.col("year") >= 2016)
       .dropDuplicates(["country_code", "year"]))

gdp.write.format("delta").mode("overwrite").saveAsTable("silver_gdp_yearly")

spark.sql("SELECT * FROM silver_gdp_yearly ORDER BY year").show(20, truncate=False)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

spark.sql("""
SELECT parameter, units, COUNT(*) rows, MIN(value) min_v, MAX(value) max_v,
       MIN(date) first_day, MAX(date) last_day
FROM Bronze_OpenAQ_Daily
GROUP BY parameter, units
ORDER BY parameter, units
""").show(30, truncate=False)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F

bronze = spark.table("Bronze_OpenAQ_Daily")

silver_aq = (bronze
    .select("date", "location_id", "location_name", "sensor_id", "parameter", "value", "units")
    .filter(F.col("value").isNotNull() & (F.col("value") >= 0))
    .dropDuplicates(["date", "sensor_id", "parameter"])
    .withColumn("year", F.year("date"))
    .withColumn("month", F.month("date")))

silver_aq.write.format("delta").mode("overwrite").saveAsTable("silver_openaq_daily")

print("bronze:", bronze.count(), "silver:", silver_aq.count(), "removed:", bronze.count() - silver_aq.count())

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

zones = spark.read.option("header", True).csv("Files/Bronze/Taxi/reference/taxi_zone_lookup.csv")
print(zones.count(), "rows")
zones.show(5, truncate=False)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import requests
import pandas as pd

API_KEY = "OPENAQ_API_KEY"   

location_ids = [1496, 857, 971, 1122, 628, 626, 666, 665, 648, 631, 664, 384, 625, 984]

headers = {"X-API-Key": API_KEY}
rows = []

for loc_id in location_ids:
    url = f"https://api.openaq.org/v3/locations/{loc_id}"
    r = requests.get(url, headers=headers)
    
    if r.status_code == 200:
        data = r.json()["results"][0]
        rows.append({
            "location_id": loc_id,
            "location_name": data.get("name"),
            "latitude": data["coordinates"]["latitude"],
            "longitude": data["coordinates"]["longitude"],
            "locality": data.get("locality"),
            "country": data.get("country", {}).get("name")
        })
        print(f"✓ {loc_id} – {data.get('name')}")
    else:
        print(f"✗ Failed for {loc_id}: {r.status_code} – {r.text[:200]}")

df_stations = pd.DataFrame(rows)
display(df_stations)

spark.createDataFrame(df_stations).write.mode("overwrite").saveAsTable("bronze_openaq_stations")
print(f"\nSaved {len(df_stations)} stations as bronze_openaq_stations")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

spark.table("bronze_openaq_stations").count()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

display(spark.table("bronze_openaq_stations").orderBy("location_id"))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

%pip install geopandas shapely -q

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from pyspark.sql import functions as F

zones_url = "https://data.cityofnewyork.us/api/geospatial/d3c5-ddgc?method=export&format=GeoJSON"
gdf_zones = gpd.read_file(zones_url)
gdf_zones = gdf_zones.to_crs(epsg=4326)

gdf_zones = gdf_zones[["location_id", "zone", "borough", "geometry"]].rename(
    columns={"location_id": "LocationID", "zone": "Zone", "borough": "Borough"}
)
gdf_zones["LocationID"] = gdf_zones["LocationID"].astype(int)

stations = spark.table("bronze_openaq_stations").toPandas()
stations["geometry"] = stations.apply(lambda r: Point(r["longitude"], r["latitude"]), axis=1)
gdf_stations = gpd.GeoDataFrame(stations, geometry="geometry", crs="EPSG:4326")

gdf_joined = gpd.sjoin_nearest(gdf_stations, gdf_zones, how="left", distance_col="distance_m")

mapping = gdf_joined[[
    "location_id", "location_name", "latitude", "longitude",
    "LocationID", "Zone", "Borough", "distance_m"
]].rename(columns={
    "LocationID": "taxi_zone_id",
    "Zone": "taxi_zone_name",
    "Borough": "taxi_borough"
})

display(mapping.sort_values("location_id"))

spark.createDataFrame(mapping).write.mode("overwrite").saveAsTable("silver_station_to_zone")
print("Saved → silver_station_to_zone")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# # day 3

# CELL ********************

%pip install shapely --quiet

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import requests
from shapely.geometry import shape, Point

url = "https://data.cityofnewyork.us/resource/8meu-9t5y.geojson?$limit=500"
r = requests.get(url, timeout=60)
print("HTTP status:", r.status_code, "| bytes:", len(r.content))

gj = r.json()
print("Features:", len(gj["features"]))
print("Properties:", list(gj["features"][0]["properties"].keys()))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Build zone geometries
zones = []
for f in gj["features"]:
    p = f["properties"]
    zones.append((int(p["locationid"]), shape(f["geometry"])))

stations = spark.table("bronze_openaq_stations").toPandas()

rows = []
for _, s in stations.iterrows():
    pt = Point(float(s["longitude"]), float(s["latitude"]))   # GeoJSON order = (lon, lat)
    inside = [zid for zid, g in zones if g.contains(pt)]
    if inside:
        zid, match_type, dist_km = inside[0], "inside", 0.0
    else:
        zid, g = min(zones, key=lambda zg: zg[1].distance(pt))
        match_type = "nearest"
        dist_km = round(g.distance(pt) * 111.0, 2)   # rough degrees -> km
    rows.append((int(s["location_id"]), s["location_name"],
                 float(s["latitude"]), float(s["longitude"]),
                 int(zid), match_type, float(dist_km)))

map_df = spark.createDataFrame(
    rows,
    "location_id int, location_name string, latitude double, longitude double, "
    "zone_id int, match_type string, distance_km double"
)

zdf = spark.table("silver_taxi_zones")
print("silver_taxi_zones columns:", zdf.columns)
key = [c for c in zdf.columns if c.lower() in ("locationid", "location_id", "zone_id")][0]

result = (map_df.join(zdf, map_df.zone_id == zdf[key], "left")
                .drop(key))

display(result)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

(result.write.mode("overwrite").format("delta")
       .option("overwriteSchema", "true")
       .saveAsTable("silver_station_to_zone"))

print(spark.table("silver_station_to_zone").count(), "rows saved")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F

st = spark.table("silver_station_to_zone")

dim_station = (st
    .withColumn("in_nyc", F.col("match_type") == "inside")
    .withColumn("zone_link_quality",
                F.when(F.col("match_type") == "inside", "exact").otherwise("approximate"))
    .withColumnRenamed("Borough", "zone_borough")
    .withColumnRenamed("Zone", "zone_name")
    .select("location_id", "location_name", "latitude", "longitude",
            "zone_id", "zone_borough", "zone_name",
            "match_type", "distance_km", "in_nyc", "zone_link_quality"))

dim_station.write.mode("overwrite").format("delta") \
    .option("overwriteSchema", "true").saveAsTable("gold_dim_station")

display(spark.table("gold_dim_station"))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

t = spark.table("silver_taxi_trips")
t.printSchema()
print(t.count(), "rows")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F

TARGET = "gold_taxi_daily"

def build_month(y, m):
    df = (spark.table("silver_taxi_trips")
          .filter((F.col("pickup_year") == y) & (F.col("pickup_month") == m)))

    agg = (df
        .withColumn("date", F.to_date("tpep_pickup_datetime"))
        .withColumn("duration_min",
                    (F.unix_timestamp("tpep_dropoff_datetime") -
                     F.unix_timestamp("tpep_pickup_datetime")) / 60.0)
        .groupBy("date", F.col("pulocationid").alias("pu_zone_id"))
        .agg(
            F.count("*").alias("trips"),
            F.sum(F.coalesce("passenger_count", F.lit(0))).alias("passengers_sum"),
            F.sum("trip_distance").alias("distance_miles_sum"),
            F.sum("duration_min").alias("duration_min_sum"),
            F.sum("fare_amount").alias("fare_usd_sum"),
            F.sum("tip_amount").alias("tip_usd_sum"),
            F.sum("tolls_amount").alias("tolls_usd_sum"),
            F.sum("total_amount").alias("total_usd_sum"),
        )
        .withColumn("pickup_year", F.lit(y))
        .withColumn("pickup_month", F.lit(m)))

    if spark.catalog.tableExists(TARGET):
        (agg.write.mode("overwrite").format("delta")
            .option("replaceWhere", f"pickup_year = {y} AND pickup_month = {m}")
            .saveAsTable(TARGET))
    else:
        (agg.write.mode("overwrite").format("delta")
            .partitionBy("pickup_year", "pickup_month")
            .saveAsTable(TARGET))

# Test on one month
build_month(2016, 1)
spark.table(TARGET).filter("pickup_year=2016 AND pickup_month=1") \
     .agg(F.sum("trips").alias("trips"), F.count("*").alias("rows")).show()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

spark.table("silver_taxi_trips").filter("pickup_year=2016 AND pickup_month=1").count()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import time

for y in range(2016, 2026):
    t0 = time.time()
    for m in range(1, 13):
        build_month(y, m)
    print(f"{y} done in {round((time.time()-t0)/60, 1)} min")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

(spark.table(TARGET).groupBy("pickup_year")
      .agg(F.sum("trips").alias("trips"))
      .orderBy("pickup_year").show())

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F

aq = spark.table("silver_openaq_daily")
aq.groupBy("parameter", "units").count().orderBy("parameter").show()

# Any station with more than one sensor for the same parameter?
(aq.groupBy("date", "location_id", "parameter")
   .agg(F.countDistinct("sensor_id").alias("sensors"))
   .filter("sensors > 1").count())

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

params = ["pm25", "no2", "o3", "co", "so2", "pm10", "no", "nox"]

aq_daily = (spark.table("silver_openaq_daily")
    .groupBy("date", "location_id", "parameter")
    .agg(F.avg("value").alias("value"))
    .groupBy("date", "location_id")
    .pivot("parameter", params)
    .agg(F.first("value")))

for p in params:
    aq_daily = aq_daily.withColumnRenamed(p, f"{p}_avg")

aq_daily = (aq_daily
    .withColumn("pickup_year", F.year("date"))
    .withColumn("pickup_month", F.month("date")))

(aq_daily.write.mode("overwrite").format("delta")
    .option("overwriteSchema", "true")
    .saveAsTable("gold_air_quality_daily"))

t = spark.table("gold_air_quality_daily")
print(t.count(), "rows")
t.select(F.min("date"), F.max("date"), F.countDistinct("location_id")).show()
t.select([F.count(F.col(f"{p}_avg")).alias(p) for p in params]).show()
display(t.orderBy("date").limit(10))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F

# ---------- gold_dim_date: 2016-01-01 .. 2025-12-31 ----------
dim_date = (spark.sql("SELECT explode(sequence(to_date('2016-01-01'), to_date('2025-12-31'), interval 1 day)) AS date")
    .withColumn("date_key", F.date_format("date", "yyyyMMdd").cast("int"))
    .withColumn("year", F.year("date"))
    .withColumn("quarter", F.quarter("date"))
    .withColumn("month", F.month("date"))
    .withColumn("month_name", F.date_format("date", "MMMM"))
    .withColumn("day", F.dayofmonth("date"))
    .withColumn("day_of_week", F.dayofweek("date"))          # 1=Sunday .. 7=Saturday
    .withColumn("day_name", F.date_format("date", "EEEE"))
    .withColumn("is_weekend", F.col("day_of_week").isin(1, 7))
    .withColumn("season",
        F.when(F.col("month").isin(12, 1, 2), "Winter")
         .when(F.col("month").isin(3, 4, 5), "Spring")
         .when(F.col("month").isin(6, 7, 8), "Summer")
         .otherwise("Autumn")))

dim_date.write.mode("overwrite").format("delta") \
    .option("overwriteSchema", "true").saveAsTable("gold_dim_date")

z = spark.table("silver_taxi_zones")
print("zone columns:", z.columns)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

spark.table("silver_fx_daily").printSchema()
spark.table("silver_gdp_yearly").printSchema()
spark.table("gold_dim_date").groupBy("year").count().orderBy("year").show()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F

# ---------- gold_dim_zone ----------
dim_zone = (spark.table("silver_taxi_zones")
    .select(F.col("LocationID").cast("int").alias("zone_id"),
            F.col("Borough").alias("borough"),
            F.col("Zone").alias("zone_name"),
            F.col("service_zone")))
dim_zone.write.mode("overwrite").format("delta") \
    .option("overwriteSchema", "true").saveAsTable("gold_dim_zone")

# ---------- gold_dim_fx: restricted to the project date range ----------
dim_fx = (spark.table("silver_fx_daily")
    .filter((F.col("date") >= "2016-01-01") & (F.col("date") <= "2025-12-31"))
    .withColumn("date_key", F.date_format("date", "yyyyMMdd").cast("int"))
    .select("date_key", "date", "usd_per_eur", "eur_per_usd", "is_filled"))
dim_fx.write.mode("overwrite").format("delta") \
    .option("overwriteSchema", "true").saveAsTable("gold_dim_fx")

# ---------- gold_dim_gdp ----------
dim_gdp = (spark.table("silver_gdp_yearly")
    .filter(F.col("year").between(2016, 2025))
    .select("country_code", "country_name", "year", "gdp_usd"))
dim_gdp.write.mode("overwrite").format("delta") \
    .option("overwriteSchema", "true").saveAsTable("gold_dim_gdp")

for t in ["gold_dim_zone", "gold_dim_fx", "gold_dim_gdp"]:
    print(t, spark.table(t).count(), "rows")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F

tx = spark.table("gold_taxi_daily")
aq = spark.table("gold_air_quality_daily")
dd = spark.table("gold_dim_date").select("date")
dz = spark.table("gold_dim_zone").select("zone_id")
fx = spark.table("gold_dim_fx").select("date")
ds = spark.table("gold_dim_station").select("location_id")

# 1. Taxi dates not in DimDate (e.g. bad timestamps outside 2016-2025)
print("taxi rows with date not in DimDate:",
      tx.join(dd, "date", "left_anti").count())

# 2. Taxi zones not in DimZone
print("taxi rows with zone not in DimZone:",
      tx.join(dz, tx.pu_zone_id == dz.zone_id, "left_anti").count())

# 3. Taxi dates without an FX rate, with the trips affected
nofx = tx.join(fx, "date", "left_anti")
nofx.agg(F.count("*").alias("rows"), F.sum("trips").alias("trips")).show()

# 4. Air quality stations not in DimStation
print("AQ rows with station not in DimStation:",
      aq.join(ds, "location_id", "left_anti").count())

# 5. AQ dates outside the project range
print("AQ rows outside 2016-2025:",
      aq.filter("date > '2025-12-31' OR date < '2016-01-01'").count())

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F

tx = spark.table("gold_taxi_daily")
fx = spark.table("gold_dim_fx").select("date")

tx.join(fx, "date", "left_anti") \
  .agg(F.min("date"), F.max("date"), F.countDistinct("date").alias("days")).show()

b = spark.table("Bronze_ECB_FX")
b.printSchema()
display(b.limit(5))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F

b = spark.table("Bronze_ECB_FX")

# Last published rate on or before 2016-01-01
last = (b.filter(F.col("TIME_PERIOD") < "2016-01-04")
         .orderBy(F.col("TIME_PERIOD").desc())
         .limit(1)
         .select("TIME_PERIOD", "OBS_VALUE").collect()[0])
rate = float(last["OBS_VALUE"])
print("Last rate before gap:", last["TIME_PERIOD"], rate)

# Build the 3 missing days
missing = (spark.sql("SELECT explode(sequence(to_date('2016-01-01'), to_date('2016-01-03'), interval 1 day)) AS date")
    .withColumn("date_key", F.date_format("date", "yyyyMMdd").cast("int"))
    .withColumn("usd_per_eur", F.lit(rate))
    .withColumn("eur_per_usd", F.lit(1.0 / rate))
    .withColumn("is_filled", F.lit(True))
    .select("date_key", "date", "usd_per_eur", "eur_per_usd", "is_filled"))

# Append only if not already there
existing = spark.table("gold_dim_fx").filter("date < '2016-01-04'").count()
if existing == 0:
    missing.write.mode("append").format("delta").saveAsTable("gold_dim_fx")

print("gold_dim_fx rows:", spark.table("gold_dim_fx").count())

# Re-check coverage
tx = spark.table("gold_taxi_daily")
fx = spark.table("gold_dim_fx").select("date")
print("taxi rows without FX:", tx.join(fx, "date", "left_anti").count())

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

for t in ["gold_dim_date","gold_dim_zone","gold_dim_station","gold_dim_fx","gold_dim_gdp",
          "gold_taxi_daily","gold_air_quality_daily"]:
    print(t, spark.table(t).count())

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F

TARGET = "gold_taxi_daypart"

def build_month_dp(y, m):
    df = (spark.table("silver_taxi_trips")
          .filter((F.col("pickup_year") == y) & (F.col("pickup_month") == m))
          .withColumn("hr", F.hour("tpep_pickup_datetime"))
          .withColumn("daypart",
              F.when(F.col("hr") < 6, "1_overnight")
               .when(F.col("hr") < 10, "2_morning_rush")
               .when(F.col("hr") < 16, "3_midday")
               .when(F.col("hr") < 20, "4_evening_rush")
               .otherwise("5_night")))
    agg = (df.withColumn("date", F.to_date("tpep_pickup_datetime"))
             .groupBy("date", F.col("pulocationid").alias("pu_zone_id"), "daypart")
             .agg(F.count("*").alias("trips"),
                  F.sum("total_amount").alias("total_usd_sum"))
             .withColumn("pickup_year", F.lit(y))
             .withColumn("pickup_month", F.lit(m)))
    if spark.catalog.tableExists(TARGET):
        (agg.write.mode("overwrite").format("delta")
            .option("replaceWhere", f"pickup_year = {y} AND pickup_month = {m}")
            .saveAsTable(TARGET))
    else:
        (agg.write.mode("overwrite").format("delta")
            .partitionBy("pickup_year", "pickup_month").saveAsTable(TARGET))

build_month_dp(2016, 1)
spark.table(TARGET).filter("pickup_year=2016 AND pickup_month=1") \
     .agg(F.sum("trips")).show()   

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import time
for y in range(2016, 2026):
    t0 = time.time()
    for m in range(1, 13):
        build_month_dp(y, m)
    print(y, "done in", round((time.time()-t0)/60, 1), "min")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F
(spark.table("gold_taxi_daypart")
      .groupBy("pickup_year").agg(F.sum("trips").alias("trips"))
      .orderBy("pickup_year").show())

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

names = [r.tableName for r in spark.sql("SHOW TABLES").collect()]
print(names)

wanted = ["bronze_ecb_fx", "bronze_worldbank_gdp",
          "silver_taxi_trips", "silver_taxi_zones", "silver_station_to_zone"]

for w in wanted:
    match = [n for n in names if n.lower() == w]
    if not match:
        print(f"\n!!! {w}: not found")
        continue
    t = match[0]
    print(f"\n=== {t} ({spark.table(t).count():,} rows) ===")
    for f in spark.table(t).schema.fields:
        print(f"{f.name}\t{f.dataType.simpleString()}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F
s = spark.table("silver_taxi_trips").where("pickup_year = 2016").agg(F.sum("total_amount")).first()[0]
g = spark.table("gold_taxi_daily").where("pickup_year = 2016").agg(F.sum("total_usd_sum")).first()[0]
print(f"silver total_amount 2016: {s:,.2f}\ngold total_usd_sum 2016:  {g:,.2f}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

spark.sql("DESCRIBE HISTORY bronze_openaq_stations") \
     .select("timestamp", "operation", "operationParameters", "notebook", "engineInfo") \
     .show(truncate=False)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
