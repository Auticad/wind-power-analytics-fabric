# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "a21dccda-0594-4fa4-a6f0-1fbcb0b02102",
# META       "default_lakehouse_name": "LH_Wind_Power_Silver",
# META       "default_lakehouse_workspace_id": "67f93c7d-b2ea-40e5-9934-a9c7ae08d4a6",
# META       "known_lakehouses": [
# META         {
# META           "id": "a21dccda-0594-4fa4-a6f0-1fbcb0b02102"
# META         },
# META         {
# META           "id": "efd78bba-7151-4683-9eac-ffbaba521ff2"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

# MAGIC %%pyspark
# MAGIC 
# MAGIC df = spark.read.format("delta").load("abfss://WindPowerAnalitics@onelake.dfs.fabric.microsoft.com/LH_Wind_Power_Bronze.Lakehouse/Tables/dbo/wind_power")
# MAGIC 
# MAGIC df.createOrReplaceTempView("bronze_wind_power")
# MAGIC df.show(5)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC SELECT * FROM dbo.wind_power LIMIT 10;

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC SELECT * FROM LH_Wind_Power_Bronze.dbo.wind_power LIMIT 10;

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Clean and enrich data
# MAGIC CREATE OR REPLACE TEMPORARY VIEW transformed_wind_power AS
# MAGIC SELECT
# MAGIC     production_id,
# MAGIC     date,
# MAGIC     turbine_name,
# MAGIC     capacity,
# MAGIC     location_name,
# MAGIC     latitude,
# MAGIC     longitude,
# MAGIC     region,
# MAGIC     status,
# MAGIC     responsible_department,
# MAGIC     wind_direction,
# MAGIC     ROUND(wind_speed, 2) AS wind_speed,
# MAGIC     ROUND(energy_produced, 2) AS energy_produced,
# MAGIC     DAY(date) AS day,
# MAGIC     MONTH(date) AS month,
# MAGIC     QUARTER(date) AS quarter,
# MAGIC     YEAR(date) AS year,
# MAGIC     REGEXP_REPLACE(time, '-', ':') AS time,
# MAGIC     CAST(SUBSTRING(time, 1, 2) AS INT) AS hour_of_day,
# MAGIC     CAST(SUBSTRING(time, 4, 2) AS INT) AS minute_of_hour,
# MAGIC     CAST(SUBSTRING(time, 7, 2) AS INT) AS second_of_minute,
# MAGIC     CASE
# MAGIC         WHEN CAST(SUBSTRING(time, 1, 2) AS INT) BETWEEN 5 AND 11 THEN 'Morning'
# MAGIC         WHEN CAST(SUBSTRING(time, 1, 2) AS INT) BETWEEN 12 AND 16 THEN 'Afternoon'
# MAGIC         WHEN CAST(SUBSTRING(time, 1, 2) AS INT) BETWEEN 17 AND 20 THEN 'Evening'
# MAGIC         ELSE 'Night'
# MAGIC     END AS time_period
# MAGIC FROM bronze_wind_power;

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC SELECT * FROM transformed_wind_power LIMIT 10;

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Drop the wind_power table in the Silver Lakehouse if it exists
# MAGIC DROP TABLE IF EXISTS LH_Wind_Power_Silver.dbo.wind_power;

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC -- Create the new wind_power table in Silver Lakehouse
# MAGIC CREATE TABLE LH_Wind_Power_Silver.dbo.wind_power
# MAGIC USING delta
# MAGIC AS
# MAGIC SELECT * FROM transformed_wind_power;

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC ALTER TABLE LH_Wind_Power_Bronze.dbo.wind_power
# MAGIC SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC ALTER TABLE LH_Wind_Power_Silver.dbo.wind_power
# MAGIC SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC DESCRIBE DETAIL LH_Wind_Power_Bronze.dbo.wind_power;

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC SHOW TBLPROPERTIES LH_Wind_Power_Bronze.dbo.wind_power;

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }
