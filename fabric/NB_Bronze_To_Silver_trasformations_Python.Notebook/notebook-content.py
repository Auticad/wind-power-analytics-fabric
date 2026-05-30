# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "efd78bba-7151-4683-9eac-ffbaba521ff2",
# META       "default_lakehouse_name": "LH_Wind_Power_Bronze",
# META       "default_lakehouse_workspace_id": "67f93c7d-b2ea-40e5-9934-a9c7ae08d4a6",
# META       "known_lakehouses": [
# META         {
# META           "id": "efd78bba-7151-4683-9eac-ffbaba521ff2"
# META         },
# META         {
# META           "id": "a21dccda-0594-4fa4-a6f0-1fbcb0b02102"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

from pyspark.sql.functions import (
    round,
    col,
    dayofmonth,
    month,
    year,
    to_date,
    quarter,
    substring,
    when,
    regexp_replace,
)


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

bronze_table_path = "abfss://WindPowerAnalitics@onelake.dfs.fabric.microsoft.com/LH_Wind_Power_Bronze.Lakehouse/Tables/dbo/wind_power"

# Load the wind_power table into a DataFrame
df = spark.read.format("delta").load(bronze_table_path)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Clean and enrich data
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

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Path to wind_power table in Silver Lakehouse
silver_table_path = "abfss://WindPowerAnalitics@onelake.dfs.fabric.microsoft.com/LH_Wind_Power_Silver.Lakehouse/Tables/dbo/wind_power"


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Save the transformed table in the Silver Lakehouse
df_transformed.write.format("delta").mode("overwrite").save(silver_table_path)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
