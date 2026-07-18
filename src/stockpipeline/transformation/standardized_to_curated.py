"""Convert standardized stock quotes from JSONL to curated Parquet."""

import sys

from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql.window import Window


args = getResolvedOptions(
    sys.argv,
    [
        "JOB_NAME",
        "SOURCE_DATABASE",
        "SOURCE_TABLE",
        "CURATED_OUTPUT_PATH",
        "REJECTED_OUTPUT_PATH",
    ],
)

spark_context = SparkContext.getOrCreate()
glue_context = GlueContext(spark_context)
spark = glue_context.spark_session

job = Job(glue_context)
job.init(args["JOB_NAME"], args)


source_dynamic_frame = glue_context.create_dynamic_frame.from_catalog(
    database=args["SOURCE_DATABASE"],
    table_name=args["SOURCE_TABLE"],
    transformation_ctx="source_standardized_quotes",
)

source_df = source_dynamic_frame.toDF()


typed_df = (
    source_df.select(
        F.upper(F.trim(F.col("symbol"))).alias("symbol"),
        F.trim(F.col("company_name")).alias("company_name"),
        F.upper(F.trim(F.col("exchange"))).alias("exchange"),
        F.upper(F.trim(F.col("currency"))).alias("currency"),
        F.col("price").cast("double").alias("price"),
        F.col("open_price").cast("double").alias("open_price"),
        F.col("high_price").cast("double").alias("high_price"),
        F.col("low_price").cast("double").alias("low_price"),
        F.col("previous_close").cast("double").alias("previous_close"),
        F.col("change").cast("double").alias("change"),
        F.col("change_percent").cast("double").alias("change_percent"),
        F.col("volume").cast("long").alias("volume"),
        F.to_timestamp(F.col("market_timestamp")).alias("market_timestamp"),
        F.to_timestamp(F.col("ingestion_timestamp")).alias(
            "ingestion_timestamp"
        ),
        F.lower(F.trim(F.col("source"))).alias("source"),
        F.input_file_name().alias("source_file"),
    )
    .withColumn(
        "rejection_reason",
        F.when(
            F.col("symbol").isNull() | (F.length(F.col("symbol")) == 0),
            F.lit("MISSING_SYMBOL"),
        )
        .when(
            F.col("price").isNull() | (F.col("price") <= 0),
            F.lit("INVALID_PRICE"),
        )
        .when(
            F.col("market_timestamp").isNull(),
            F.lit("INVALID_MARKET_TIMESTAMP"),
        )
        .when(
            F.col("ingestion_timestamp").isNull(),
            F.lit("INVALID_INGESTION_TIMESTAMP"),
        )
        .when(
            F.col("volume").isNotNull() & (F.col("volume") < 0),
            F.lit("NEGATIVE_VOLUME"),
        )
        .when(
            F.col("high_price").isNotNull()
            & F.col("low_price").isNotNull()
            & (F.col("high_price") < F.col("low_price")),
            F.lit("HIGH_BELOW_LOW"),
        ),
    )
)


rejected_df = (
    typed_df.filter(F.col("rejection_reason").isNotNull())
    .withColumn("rejected_at", F.current_timestamp())
    .withColumn("year", F.date_format(F.col("rejected_at"), "yyyy"))
    .withColumn("month", F.date_format(F.col("rejected_at"), "MM"))
    .withColumn("day", F.date_format(F.col("rejected_at"), "dd"))
)


valid_df = typed_df.filter(F.col("rejection_reason").isNull()).drop(
    "rejection_reason",
    "source_file",
)


latest_record_window = Window.partitionBy(
    "symbol",
    "market_timestamp",
).orderBy(F.col("ingestion_timestamp").desc())


curated_df = (
    valid_df.withColumn(
        "record_rank",
        F.row_number().over(latest_record_window),
    )
    .filter(F.col("record_rank") == 1)
    .drop("record_rank")
    .withColumn("year", F.date_format(F.col("market_timestamp"), "yyyy"))
    .withColumn("month", F.date_format(F.col("market_timestamp"), "MM"))
    .withColumn("day", F.date_format(F.col("market_timestamp"), "dd"))
)


if not curated_df.rdd.isEmpty():
    curated_dynamic_frame = DynamicFrame.fromDF(
        curated_df,
        glue_context,
        "curated_quotes",
    )

    glue_context.write_dynamic_frame.from_options(
        frame=curated_dynamic_frame,
        connection_type="s3",
        connection_options={
            "path": args["CURATED_OUTPUT_PATH"],
            "partitionKeys": ["year", "month", "day"],
        },
        format="parquet",
        format_options={
            "compression": "snappy",
            "useGlueParquetWriter": True,
        },
        transformation_ctx="write_curated_quotes",
    )


if not rejected_df.rdd.isEmpty():
    rejected_dynamic_frame = DynamicFrame.fromDF(
        rejected_df,
        glue_context,
        "rejected_quotes",
    )

    glue_context.write_dynamic_frame.from_options(
        frame=rejected_dynamic_frame,
        connection_type="s3",
        connection_options={
            "path": args["REJECTED_OUTPUT_PATH"],
            "partitionKeys": ["year", "month", "day"],
        },
        format="parquet",
        format_options={
            "compression": "snappy",
            "useGlueParquetWriter": True,
        },
        transformation_ctx="write_rejected_quotes",
    )


job.commit()