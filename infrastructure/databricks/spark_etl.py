"""
Databricks PySpark ETL Job - AI-Driven Video Evidence Analysis
============================================================
This script runs as a batch cluster job in Databricks.
It reads raw JSON metadata extracted by Azure AI Services, standardizes schemas,
runs data quality checks, aggregates entities, and saves the cleaned records to a Delta Table.
"""

import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, explode, when, lit, count, current_timestamp
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, ArrayType, IntegerType, MapType
)

# Initialize Spark Session
spark = SparkSession.builder \
    .appName("VideoEvidenceETL") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

def run_etl(input_path: str, output_table: str):
    print(f"Starting Video Evidence ETL pipeline. Input path: {input_path}")
    
    # 1. Define schema for Azure raw metadata extracts
    raw_schema = StructType([
        StructField("case_id", StringType(), True),
        StructField("video_id", StringType(), True),
        StructField("objects", ArrayType(
            StructType([
                StructField("label", StringType(), True),
                StructField("timestamp", DoubleType(), True),
                StructField("confidence", DoubleType(), True)
            ])
        ), True),
        StructField("persons", ArrayType(
            StructType([
                StructField("person_id", StringType(), True),
                StructField("timestamp", DoubleType(), True),
                StructField("confidence", DoubleType(), True),
                StructField("attributes", MapType(StringType(), StringType()), True)
            ])
        ), True),
        StructField("vehicles", ArrayType(
            StructType([
                StructField("vehicle_id", StringType(), True),
                StructField("timestamp", DoubleType(), True),
                StructField("confidence", DoubleType(), True),
                StructField("license_plate", StringType(), True),
                StructField("color", StringType(), True),
                StructField("type", StringType(), True)
            ])
        ), True)
    ])
    
    # 2. Read raw metadata JSON from DBFS/S3/ADLS
    df_raw = spark.read.schema(raw_schema).json(input_path)
    
    # 3. Data Quality Checks & Cleaning (Filtering low confidence records)
    min_confidence = 0.70
    
    # Explode objects and filter
    df_objects = df_raw.select(
        col("case_id"),
        col("video_id"),
        explode("objects").alias("obj")
    ).select(
        col("case_id"),
        col("video_id"),
        col("obj.label").alias("label"),
        col("obj.timestamp").alias("timestamp"),
        col("obj.confidence").alias("confidence")
    ).filter(col("confidence") >= min_confidence)
    
    # Explode persons and filter
    df_persons = df_raw.select(
        col("case_id"),
        col("video_id"),
        explode("persons").alias("p")
    ).select(
        col("case_id"),
        col("video_id"),
        col("p.person_id").alias("person_id"),
        col("p.timestamp").alias("timestamp"),
        col("p.confidence").alias("confidence"),
        col("p.attributes").alias("attributes")
    ).filter(col("confidence") >= min_confidence)

    # Explode vehicles and filter
    df_vehicles = df_raw.select(
        col("case_id"),
        col("video_id"),
        explode("vehicles").alias("v")
    ).select(
        col("case_id"),
        col("video_id"),
        col("v.vehicle_id").alias("vehicle_id"),
        col("v.timestamp").alias("timestamp"),
        col("v.confidence").alias("confidence"),
        col("v.license_plate").alias("license_plate"),
        col("v.color").alias("color"),
        col("v.type").alias("type")
    ).filter(col("confidence") >= min_confidence)

    # 4. Aggregations & Metrics Calculation
    # Determine presence of weapons
    df_weapons = df_objects.withColumn(
        "is_weapon",
        col("label").rlike("(?i)(gun|weapon|knife|pistol|rifle|handgun)")
    ).filter(col("is_weapon") == True)

    agg_objects = df_objects.groupBy("case_id", "video_id").agg(count("label").alias("objects_count"))
    agg_persons = df_persons.groupBy("case_id", "video_id").agg(count("person_id").alias("people_count"))
    agg_vehicles = df_vehicles.groupBy("case_id", "video_id").agg(count("vehicle_id").alias("vehicles_count"))
    agg_weapons = df_weapons.groupBy("case_id", "video_id").agg(count("label").alias("weapons_count"))

    # Join aggregates together
    df_metrics = agg_objects \
        .join(agg_persons, ["case_id", "video_id"], "outer") \
        .join(agg_vehicles, ["case_id", "video_id"], "outer") \
        .join(agg_weapons, ["case_id", "video_id"], "outer") \
        .na.fill(0) \
        .withColumn("etl_processed_at", current_timestamp())

    # 5. Write metrics and cleaned tables to Unity Catalog / Delta Lake
    print(f"Writing aggregated results to Delta Table: {output_table}")
    df_metrics.write \
        .format("delta") \
        .mode("overwrite") \
        .saveAsTable(output_table)
    
    # Save detail tables for deeper analyst querying
    df_objects.write.format("delta").mode("overwrite").saveAsTable(f"{output_table}_objects")
    df_persons.write.format("delta").mode("overwrite").saveAsTable(f"{output_table}_persons")
    df_vehicles.write.format("delta").mode("overwrite").saveAsTable(f"{output_table}_vehicles")
    
    print("ETL job finished successfully.")

if __name__ == "__main__":
    # In production, these parameters are passed from Databricks Job Parameters
    in_path = sys.argv[1] if len(sys.argv) > 1 else "/dbfs/tmp/evidence/raw_metadata.json"
    out_table = sys.argv[2] if len(sys.argv) > 2 else "evidence.processed_metadata"
    run_etl(in_path, out_table)
