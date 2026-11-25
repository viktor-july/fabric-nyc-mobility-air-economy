# Urban Mobility, Air Quality and Economy in NYC: Final Write-up


## 1. Summary

This project built a single analytics platform on Microsoft Fabric that combines three open data sources: NYC yellow taxi trips (mobility), OpenAQ air quality (environment) and World Bank GDP with ECB exchange rates (economy). Data moves through a Bronze → Silver → Gold design, ends in a Warehouse star schema, and is reported in a four-page Power BI report with row-level security.

**Main findings**

1. **Taxi volume does not explain air quality in this data.** Daily yellow taxi trips and daily PM2.5 show no usable relationship, at city level, zone level or by time of day.
2. **Yellow taxi use fell by two thirds while GDP grew by about two thirds.** Trips fell from 130.1M (2016) to 44.2M (2025). US GDP rose from 18.80 to 30.77 trillion USD. PM2.5 stayed roughly flat, apart from the 2023 wildfire year.
3. **Fares per trip rose a lot, and the currency matters.** Average revenue per trip rose from 16.27 USD (2016) to 28.88 USD (2025). In 2025 the dollar fare rose 0.8% versus 2024, but in euros it fell 3.6%, because the euro strengthened.
4. **The data cannot prove or disprove a causal link.** Yellow taxis are only a small and shrinking slice of NYC traffic, air quality data is daily only, and no NYC station measures NO2.

**Platform outcome:** 642,083,189 cleaned trips, 98,718 air quality measurements, 3,966 daily FX rates and 10 years of GDP are available in one governed model, validated end to end against the source counts.

---

## 2. Scope and approach

| Area | What was built |
|---|---|
| Bronze | 120 monthly taxi Parquet files (9.76 GB), OpenAQ daily table, ECB FX table, World Bank GDP table, station coordinates |
| Silver | Cleaned and unified taxi trips, air quality, FX, GDP, taxi zones, station-to-zone mapping |
| Gold | Daily taxi and air quality facts, daypart fact, five dimensions (Lakehouse staging) |
| Warehouse | Star schema: 5 dimensions, 3 fact tables |
| Semantic model | Direct Lake, 7 relationships, measures, 2 RLS roles |
| Report | 4 analysis pages |
| Automation | Dataflow daily refresh, semantic model auto-update. Pipeline, notebook and Warehouse load run manually |

Details are in `01_data_dictionary.md` and `02_lineage_and_governance.md`.

**Data quality at a glance**

| Check | Result |
|---|---|
| Taxi rows removed in Silver (January 2016 sample) | 0.78% |
| Yearly trip totals: Silver vs Gold vs Warehouse | Match exactly (642,083,189) |
| Orphan keys (dates, zones, stations) | 0 |
| Air quality rows removed in Silver | 14 of 98,732 |
| RLS test, `Borough_Manhattan` | 579,967,984 trips, equal to the SQL check |

---

## 3. Findings by key question

### Q1. How does traffic intensity (trips per day) relate to air quality (PM2.5)?

Daily Pearson correlation between trips and PM2.5 per year, citywide (8 NYC stations with PM2.5):

| Year | r | Days |
|---|---|---|
| 2016 | 0.06 | 133 |
| 2017 | -0.02 | 326 |
| 2018 | -0.08 | 313 |
| 2019 | -0.03 | 233 |
| 2020 | 0.32 | 356 |
| 2021 | 0.03 | 347 |
| 2022 | -0.24 | 363 |
| 2023 | 0.06 | 321 |
| 2024 | -0.19 | 366 |
| 2025 | 0.02 | 350 |

**Reading:** the values move around zero with changing signs. There is no consistent positive or negative relationship. The scatter chart (daily trips vs PM2.5) is a shapeless cloud. The few high PM2.5 points (60–145 µg/m³) are the 2023 wildfire days, which occurred at average trip levels.

**Conclusion:** no usable relationship between daily yellow taxi volume and PM2.5.

### Q2. Which zones or times of day show the strongest link between taxi demand and pollution peaks?

**By zone** (taxi pickups in the zone that contains a station, correlated with that station's PM2.5):
- 8 stations returned a result, with r between -0.06 and +0.09 and no pattern.
- Pfizer Lab (zone 31) is missing because it measures O3 only and has no PM2.5.
- Bronx zones are thin (about 6–8 pickups per day), so their results are weak.

**By daypart** (overnight, morning rush, midday, evening rush, night):
- Pooled r is between -0.05 and -0.016 for all five dayparts.
- No daypart is consistently stronger across years.
- 2020 is positive for all dayparts (+0.21 to +0.34). This is probably trend and seasonality during the COVID collapse and recovery (hypothesis, not tested).
- Midday is the most negative in 2022 and 2024 (-0.23, -0.21), but not in other years.

**Busiest pickup zones** (report): Upper East Side South, Midtown Center and Upper East Side North are at the top. Manhattan accounts for 90.3% of all trips (579,967,984 of 642,083,189).
**Busiest daypart:** midday (10:00–16:00) has the most trips in total, 201.1M or 31.3% of all trips. Per hour, the evening rush (16:00–20:00) is the busiest with 38.5M trips per hour of daypart (total trips divided by the length of the daypart), ahead of midday (33.5M) and night (33.2M). The morning rush is lower (23.1M), and overnight is the quietest (10.3M).

**Conclusion:** no zone or time of day shows a meaningful link. Taxi demand is concentrated in Manhattan, but the Manhattan stations do not show a matching pollution signal at daily resolution.

### Q3. Average revenue per trip in USD vs EUR, and the effect of the exchange rate

| Year | USD per trip | EUR per trip |
|---|---|---|
| 2016 | 16.27 | 14.69 |
| 2017 | 16.26 | 14.44 |
| 2018 | 16.34 | 13.84 |
| 2019 | 19.09 | 17.06 |
| 2020 | 18.31 | 16.24 |
| 2021 | 19.73 | 16.78 |
| 2022 | 21.73 | 20.74 |
| 2023 | 28.94 | 26.77 |
| 2024 | 28.64 | 26.48 |
| 2025 | 28.88 | 25.54 |
| **All years** | **19.58** | **17.52** |

EUR values use the ECB rate of each day (daily revenue × daily `eur_per_usd`).

**Reading**
- The USD fare per trip rose about 77.5% from 2016 to 2025. In EUR it rose about 74%.
- **FX example, 2025 vs 2024:** USD per trip +0.8%, EUR per trip -3.6%. The euro strengthened from 1.082 to 1.130 USD per EUR. A flat dollar fare therefore looks like a falling fare for a euro-based observer.
- Two jumps stand out: 2019 and 2023. Both are probably fee or surcharge changes (for example a congestion surcharge), but this was **not verified**. The fee columns were not analysed.

**Conclusion:** exchange rate movements can change the sign of a year-on-year fare trend. Reporting in both currencies is useful for international comparison.

### Q4. Over multiple years, do we see mobility and economic growth at the expense of environmental quality?

| Year | Trips | Revenue (USD bn) | Avg PM2.5 (µg/m³) | PM2.5 days | Stations | GDP (USD tn) |
|---|---|---|---|---|---|---|
| 2016 | 130.1M | 2.12 | 6.63 | 133 | 8 | 18.80 |
| 2017 | 112.5M | 1.83 | 6.94 | 326 | 8 | 19.61 |
| 2018 | 101.9M | 1.66 | 7.36 | 313 | 7 | 20.66 |
| 2019 | 83.5M | 1.59 | 6.86 | 233 | 7 | 21.54 |
| 2020 | 24.1M | 0.44 | 6.28 | 356 | 7 | 21.38 |
| 2021 | 30.3M | 0.60 | 7.38 | 347 | 8 | 23.73 |
| 2022 | 38.8M | 0.84 | 7.36 | 363 | 6 | 26.05 |
| 2023 | 37.2M | 1.08 | 9.87 | 321 | 8 | 27.81 |
| 2024 | 39.7M | 1.14 | 7.45 | 366 | 8 | 29.30 |
| 2025 | 44.2M | 1.28 | 7.75 | 350 | 8 | 30.77 |

**Reading**
- GDP grew by about 64% (18.80 to 30.77). Taxi trips fell by about 66%. Revenue fell by about 40% (2.12 to 1.28 bn), because the fare per trip rose.
- PM2.5 is flat to slightly up. The 2023 value (9.87) is inflated by the June 2023 Canadian wildfire smoke: on 2023-06-07 four NYC stations read 170–200 µg/m³ at the same time.
- 2020 shows the lowest trips and the lowest PM2.5 (6.28), but the 2020 drop in trips is a COVID effect, and 2021 PM2.5 (7.38) is back at the 2018 level while trips were still 70% below 2018. This weakens a simple "fewer taxis, cleaner air" story.
- The PM2.5 averages are not strictly like-for-like: station count varies (6–8) and 2016 has only 133 days.

**Conclusion:** there is no sign of growth at the expense of air quality, and no sign of improvement either. The fall in yellow taxi trips is mostly explained by ride-hailing and COVID, which this data does not contain.

---

## 4. Overall interpretation

The unified view shows that **daily yellow taxi volume does not explain PM2.5 variation in NYC**. Plausible reasons, none of them tested here:
- Yellow taxis are one slice of road traffic. Ride-hailing, delivery vehicles, trucks and private cars are not in the data.
- PM2.5 in the New York region is strongly driven by weather and regional transport (wildfire smoke is the clearest case in this data), not by local daily traffic counts.
- Daily averages hide the hourly rush-hour effects where a traffic link would be most visible.

This is a result about the data available, not proof that traffic has no effect on air quality.

---

## 5. Limitations

| # | Limitation | Effect on conclusions |
|---|---|---|
| 1 | Air quality is daily only | Hourly traffic-pollution links cannot be tested |
| 2 | Yellow taxis are a small, shrinking share of NYC traffic | Traffic intensity is understated, and its trend is confounded by ride-hailing |
| 3 | No NO2 measurement at any NYC station | NO2 analysis uses Jersey City only, as a regional proxy, not NYC |
| 4 | Station coverage is uneven (6–8 stations, 2016 has 133 days) | Year-to-year PM2.5 averages are not strictly comparable |
| 5 | 5 of 14 stations are in New Jersey, snapped to the nearest NYC zone | Excluded from NYC measures. Zone-level analysis uses the 9 exact stations (8 with PM2.5) |
| 6 | Sensor anomalies (Bayonne NO2, May 2022; other single NJ station spikes) | Not used in charts. Source data left unchanged |
| 7 | 2023 wildfire smoke | Distorts the 2023 PM2.5 average. Kept as real data |
| 8 | GDP is USA only | Macro context is national, not NYC |
| 9 | 2019 and 2023 fare jumps not explained | Fare trends reflect unknown fee changes |
| 10 | Correlation analysis only, no control for weather or season | Weak correlations cannot be read as causal effects |
| 11 | Dayparts have different lengths | Daypart bars are not per-hour comparable. Use the trips-per-hour figures in Q2 |

---

## 6. Recommendations and next steps

**Analytics**
1. Add **weather data** (temperature, wind, precipitation). This is the most likely missing explanatory variable.
2. Add **ride-hailing (FHV/HVFHV) trip data** from the same TLC source, to cover the traffic that replaced yellow taxis.
3. Look for **hourly air quality** data, so the rush-hour question can be tested directly.
4. Verify the **2019 and 2023 fare jumps** by analysing the surcharge and fee columns.
5. Test **2020 per month** and the **2023 wildfire period by month**, to separate trend and event effects.

**Platform**
1. Build **one orchestration pipeline**: Dataflow → Notebook → Warehouse load → semantic model refresh, and schedule it. This closes the main automation gap (automatic refresh currently stops at Bronze).
2. Add **refresh failure alerts**.
3. Consider **Purview** for catalog and classification if the platform grows.
4. Extend GDP to the **euro area**, if the EUR comparison should include macro context.

---

## 7. Deliverables checklist

| Deliverable (from the scope) | Status | Where |
|---|---|---|
| Fabric Lakehouse (Bronze, Silver, Gold) with three datasets | Done | `LH_Taxi` |
| ETL pipelines and Dataflows for ingestion | Done. Dataflow refresh is automatic. Pipeline is run manually by design | `PL_Ingestion`, Dataflow Gen2 |
| Fabric Warehouse with star schema | Done and validated | `Warehouse` |
| Visualizations (mobility, environment, economy) | Done | `RPT_Mobility_Env_Economy` |
| Documentation: data dictionary | Done | `01_data_dictionary.md` |
| Documentation: lineage diagrams | Done | `02_lineage_and_governance.md`, Part A |
| Documentation: governance policies | Done | `02_lineage_and_governance.md`, Part B |
| Governance: RLS | Done and tested | Semantic model roles |
| Governance: lineage view | Reviewed in Fabric | Workspace lineage view |
| Governance: Purview | Not implemented (optional) | |
| Refresh schedule | Partly automated | Section 2 |

## 8. Expected outcomes: result

| Expected outcome | Result |
|---|---|
| Unified view of how urban mobility affects air quality | Delivered. The finding is that yellow taxi volume shows no usable link to PM2.5 in this data |
| Convert taxi economics into global terms (GDP, FX) | Delivered. Revenue and fare per trip in USD and EUR, with GDP context. The 2025 example shows how FX changes the trend |
| Demonstration of the full Fabric stack | Delivered: Lakehouse, Pipeline, Dataflow Gen2, Notebook (PySpark), Warehouse, Direct Lake semantic model, Power BI, RLS, lineage view |
| Replicable framework for other open datasets | Delivered. The Bronze → Silver → Gold pattern, naming rules, runbook and validation queries can be reused. Weather, ride-hailing and traffic sensors would follow the same steps |

---

## 9. Lessons learned (technical)

- A Dataflow query needs a Data destination pointing at the Lakehouse, otherwise data goes to the hidden staging lakehouse.
- A Direct Lake model can block "Test as role" with an SSO error. Signing in again with fresh credentials resolved it.
- A DAX measure that uses `MAX` over a related table inside `SUMX` needs `CALCULATE`, or every day gets the highest value of the period (this gave wrong EUR values until fixed).
- A measure cannot share a name with a column (names are case-insensitive).
- In the Warehouse, run `DROP`, `CREATE`, `INSERT` and `ALTER` as separate queries. CTAS makes all columns nullable, so dimensions with keys were created with explicit `NOT NULL` columns.
- Check the data before debugging a measure. The "blank" NYC NO2 measure was correct: there is no NYC NO2 data.
- Compare within the same year or month, not only across years, because the taxi decline is mixed with ride-hailing, COVID and regulation changes.
