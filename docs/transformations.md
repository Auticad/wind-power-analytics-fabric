# Trasformazioni dati — Bronze → Silver → Gold

## Bronze → Silver

Obiettivo: partire dai dati raw e produrre una tabella arricchita con componenti temporali e normalizzazione del formato.

### Trasformazioni applicate

| Campo | Operazione | Motivazione |
|-------|-----------|-------------|
| `wind_speed` | `ROUND(..., 2)` | Riduce la precisione ridondante (>2 decimali non significativi per m/s) |
| `energy_produced` | `ROUND(..., 2)` | Coerenza con la granularità di misura (kWh a 2 decimali) |
| `time` | `REGEXP_REPLACE('-', ':')` | Il raw usa `-` come separatore: `00-10-00` → `00:10:00` (standard ISO) |
| `day` | `DAY(date)` | Componente per analisi giornaliera |
| `month` | `MONTH(date)` | Componente per analisi mensile e stagionalità |
| `quarter` | `QUARTER(date)` | Componente trimestrale |
| `year` | `YEAR(date)` | Componente annuale |
| `hour_of_day` | `CAST(SUBSTRING(time, 1, 2) AS INT)` | Ore per analisi intraday |
| `minute_of_hour` | `CAST(SUBSTRING(time, 4, 2) AS INT)` | Minuti |
| `second_of_minute` | `CAST(SUBSTRING(time, 7, 2) AS INT)` | Secondi (zero nel dataset a 10 min) |
| `time_period` | CASE / WHEN su `hour_of_day` | Fascia oraria leggibile per aggregazioni in Power BI |

### Versione PySpark (NB_Bronze_To_Silver_Transformations_Python)

```python
from pyspark.sql.functions import (
    round, col, dayofmonth, month, year,
    to_date, quarter, substring, when, regexp_replace,
)

bronze_table_path = "abfss://WindPowerAnalitics@onelake.dfs.fabric.microsoft.com/LH_Wind_Power_Bronze.Lakehouse/Tables/dbo/wind_power"
df = spark.read.format("delta").load(bronze_table_path)

df_transformed = (
    df.withColumn("wind_speed", round(col("wind_speed"), 2))
    .withColumn("energy_produced", round(col("energy_produced"), 2))
    .withColumn("day", dayofmonth(col("date")))
    .withColumn("month", month(col("date")))
    .withColumn("quarter", quarter(col("date")))
    .withColumn("year", year(col("date")))
    .withColumn("time", regexp_replace(col("time"), "-", ":"))
    .withColumn("hour_of_day", substring(col("time"), 1, 2).cast("int"))
    .withColumn("minute_of_hour", substring(col("time"), 4, 2).cast("int"))
    .withColumn("second_of_minute", substring(col("time"), 7, 2).cast("int"))
    .withColumn(
        "time_period",
        when((col("hour_of_day") >= 5) & (col("hour_of_day") < 12), "Morning")
        .when((col("hour_of_day") >= 12) & (col("hour_of_day") < 17), "Afternoon")
        .when((col("hour_of_day") >= 17) & (col("hour_of_day") < 21), "Evening")
        .otherwise("Night"),
    )
)

silver_table_path = "abfss://WindPowerAnalitics@onelake.dfs.fabric.microsoft.com/LH_Wind_Power_Silver.Lakehouse/Tables/dbo/wind_power"
df_transformed.write.format("delta").mode("overwrite").save(silver_table_path)
```

### Versione SQL (NB_Bronze_To_Silver_Transformations_SQL)

```sql
-- Step 1: crea vista temporanea sul Bronze
CREATE OR REPLACE TEMPORARY VIEW bronze_wind_power AS
SELECT * FROM WindPowerAnalytics.LH_Wind_Power_Bronze.dbo.wind_power;

-- Step 2: applica trasformazioni
CREATE OR REPLACE TEMPORARY VIEW transformed_wind_power AS
SELECT
    production_id, date, turbine_name, capacity,
    location_name, latitude, longitude, region,
    status, responsible_department, wind_direction,
    ROUND(wind_speed, 2) AS wind_speed,
    ROUND(energy_produced, 2) AS energy_produced,
    DAY(date) AS day,
    MONTH(date) AS month,
    QUARTER(date) AS quarter,
    YEAR(date) AS year,
    REGEXP_REPLACE(time, '-', ':') AS time,
    CAST(SUBSTRING(time, 1, 2) AS INT) AS hour_of_day,
    CAST(SUBSTRING(time, 4, 2) AS INT) AS minute_of_hour,
    CAST(SUBSTRING(time, 7, 2) AS INT) AS second_of_minute,
    CASE
        WHEN CAST(SUBSTRING(time, 1, 2) AS INT) BETWEEN 5 AND 11 THEN 'Morning'
        WHEN CAST(SUBSTRING(time, 1, 2) AS INT) BETWEEN 12 AND 16 THEN 'Afternoon'
        WHEN CAST(SUBSTRING(time, 1, 2) AS INT) BETWEEN 17 AND 20 THEN 'Evening'
        ELSE 'Night'
    END AS time_period
FROM bronze_wind_power;

-- Step 3: crea tabella Silver da vista trasformata
DROP TABLE IF EXISTS WindPowerAnalytics.LH_Wind_Power_Silver.dbo.wind_power;

CREATE TABLE WindPowerAnalytics.LH_Wind_Power_Silver.dbo.wind_power
USING delta
AS SELECT * FROM transformed_wind_power;
```

**Differenza tra le due versioni:** la versione SQL usa `BETWEEN 5 AND 11` per Morning (include l'ora 11), mentre la Python usa `< 12`. Il risultato è identico. La versione SQL usa `BETWEEN 12 AND 16` per Afternoon (esclude 17), coerente con Python `< 17`.

---

## Silver → Gold (NB_Silver_To_Gold_Transformations_Python)

Obiettivo: trasformare la tabella Silver flat in uno star schema a 5 tabelle.

### Logica di costruzione

```python
from pyspark.sql.window import Window
from pyspark.sql.functions import row_number

silver_table_path = "abfss://WindPowerAnalitics@onelake.dfs.fabric.microsoft.com/LH_Wind_Power_Silver.Lakehouse/Tables/dbo/wind_power"
df = spark.read.format("delta").load(silver_table_path)

# Dimension tables via distinct() + rinomina PK
date_dim = df.select("date", "day", "month", "quarter", "year") \
             .distinct().withColumnRenamed("date", "date_id")

time_dim = df.select("time", "hour_of_day", "minute_of_hour", "second_of_minute", "time_period") \
             .distinct().withColumnRenamed("time", "time_id")

# Chiavi surrogate per turbine e status
turbine_dim = df.select("turbine_name", "capacity", "location_name", "latitude", "longitude", "region") \
                .distinct() \
                .withColumn("turbine_id", row_number().over(
                    Window.orderBy("turbine_name", "capacity", "location_name", "latitude", "longitude", "region")
                ))

operational_status_dim = df.select("status", "responsible_department") \
                           .distinct() \
                           .withColumn("status_id", row_number().over(
                               Window.orderBy("status", "responsible_department")
                           ))

# Join per ottenere le FK nella fact table
df = df.join(turbine_dim, ["turbine_name", "capacity", "location_name", "latitude", "longitude", "region"], "left") \
       .join(operational_status_dim, ["status", "responsible_department"], "left")

fact_table = df.select(
    "production_id", "date", "time", "turbine_id", "status_id",
    "wind_speed", "wind_direction", "energy_produced"
).withColumnRenamed("date", "date_id").withColumnRenamed("time", "time_id")
```

### Scrittura in Gold

Tutte le tabelle usano `mode("overwrite")` — riscrittura completa a ogni run.

```
gold_date_dim_path              → dbo/dim_date
gold_time_dim_path              → dbo/dim_time
gold_turbine_dim_path           → dbo/dim_turbine
gold_operational_status_dim_path→ dbo/dim_operational_status
gold_fact_table_path            → dbo/fact_wind_power
```

### Limitazioni note

1. **Chiavi surrogate non stabili tra run:** `row_number()` assegna ID in base all'ordinamento. Se le dimension cambiano (nuove turbine, nuovi stati), gli ID si ricalcolano e il Semantic Model Power BI potrebbe perdere la coerenza delle relazioni.
   - **Soluzione consigliata in produzione:** usare hash deterministici (es. `md5(turbine_name || capacity || ...)`) oppure una tabella di mapping persistente.

2. **Overwrite completo della Gold:** ogni esecuzione riscrive tutte le 5 tabelle. Su dataset grandi diventa costoso.
   - **Soluzione:** Delta `MERGE INTO` per aggiornamenti incrementali.
