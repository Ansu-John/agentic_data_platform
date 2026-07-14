import argparse
import logging
import sys
from typing import Optional
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import current_timestamp, lit
from pyspark.errors import AnalysisException

# -------------------------------------------------------------------
# Configuration & Logging
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("RawToIcebergPipeline")

class IcebergIngestionPipeline:
    """
    Enterprise PySpark Pipeline for ingesting raw data into Apache Iceberg tables.
    Supports idempotency via MERGE INTO and schema evolution.
    """

    def __init__(self, source_path: str, db_name: str, table_name: str, silver_bucket: str, merge_key: str):
        self.source_path = source_path
        self.db_name = db_name
        self.table_name = table_name
        self.silver_bucket = silver_bucket
        self.merge_key = merge_key
        self.iceberg_table_identifier = f"glue_catalog.{self.db_name}.{self.table_name}"
        self.s3_location = f"s3://{self.silver_bucket}/{self.db_name}/{self.table_name}/"
        
        self.spark = self._initialize_spark_session()

    def _initialize_spark_session(self) -> SparkSession:
        """Initializes a SparkSession optimized for Apache Iceberg and AWS Glue."""
        logger.info("Initializing SparkSession with Iceberg extensions...")
        try:
            return SparkSession.builder \
                .appName(f"Ingest-{self.table_name}") \
                .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
                .config("spark.sql.catalog.glue_catalog", "org.apache.iceberg.spark.SparkCatalog") \
                .config("spark.sql.catalog.glue_catalog.catalog-impl", "org.apache.iceberg.aws.glue.GlueCatalog") \
                .config("spark.sql.catalog.glue_catalog.io-impl", "org.apache.iceberg.aws.s3.S3FileIO") \
                .config("spark.sql.iceberg.handle-timestamp-without-timezone", "true") \
                .getOrCreate()
        except Exception as e:
            logger.critical(f"Failed to initialize SparkSession: {str(e)}", exc_info=True)
            sys.exit(1)

    def read_source_data(self) -> Optional[DataFrame]:
        """Reads raw data from S3, applying schema inference."""
        logger.info(f"Reading raw data from: {self.source_path}")
        try:
            # Assuming JSON payload from the Lambda trigger. 
            # In a highly dynamic setup, format could be passed as an arg.
            df = self.spark.read.option("multiLine", "true").json(self.source_path)
            
            if df.isEmpty():
                logger.warning(f"Source path {self.source_path} resulted in an empty DataFrame. Aborting.")
                return None
                
            return df
        except AnalysisException as e:
            logger.error(f"Spark Analysis Exception while reading data: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error reading source data: {str(e)}", exc_info=True)
            raise

    def apply_transformations(self, df: DataFrame) -> DataFrame:
        """Applies standard metadata columns required for data governance."""
        logger.info("Applying audit transformations...")
        # Inject standard audit columns
        return df \
            .withColumn("_ingest_timestamp", current_timestamp()) \
            .withColumn("_source_file", lit(self.source_path))

    def write_to_iceberg(self, df: DataFrame) -> None:
        """
        Executes an idempotent write to Iceberg.
        Creates the table if it does not exist, otherwise performs a MERGE INTO.
        """
        logger.info(f"Preparing to write to {self.iceberg_table_identifier}")
        
        # Check if table exists in the Glue Catalog
        table_exists = self.spark.catalog.tableExists(self.iceberg_table_identifier)

        if not table_exists:
            logger.info(f"Table does not exist. Creating {self.iceberg_table_identifier} at {self.s3_location}")
            df.writeTo(self.iceberg_table_identifier) \
                .tableProperty("location", self.s3_location) \
                .tableProperty("format-version", "2") \
                .tableProperty("write.merge.mode", "merge-on-read") \
                .createOrReplace()
            logger.info("Table created successfully.")
        else:
            logger.info(f"Table exists. Executing MERGE INTO using key: {self.merge_key}")
            # Register the incoming dataframe as a temporary view for Spark SQL
            df.createOrReplaceTempView("updates")
            
            # Construct dynamic MERGE INTO statement
            merge_query = f"""
            MERGE INTO {self.iceberg_table_identifier} t
            USING updates s
            ON t.{self.merge_key} = s.{self.merge_key}
            WHEN MATCHED THEN UPDATE SET *
            WHEN NOT MATCHED THEN INSERT *
            """
            
            try:
                self.spark.sql(merge_query)
                logger.info("MERGE operation completed successfully.")
            except Exception as e:
                logger.error(f"Failed to execute MERGE statement: {str(e)}", exc_info=True)
                raise

    def run(self)-> None:
        """Orchestrates the pipeline execution lifecycle."""
        try:
            df_raw = self.read_source_data()
            if df_raw is None:
                return

            if self.merge_key not in df_raw.columns:
                raise ValueError(f"Primary merge key '{self.merge_key}' not found in source data.")

            df_transformed = self.apply_transformations(df_raw)
            self.write_to_iceberg(df_transformed)
            
        finally:
            logger.info("Stopping SparkSession...")
            self.spark.stop()


def parse_arguments()-> argparse.Namespace:
    """Robust argument parsing for EMR job submission."""
    parser = argparse.ArgumentParser(description="Raw to Iceberg Ingestion Job")
    parser.add_argument("--source-path", required=True, help="S3 URI of the raw source file")
    parser.add_argument("--db-name", required=True, help="Glue Catalog Database Name")
    parser.add_argument("--table-name", required=True, help="Target Iceberg Table Name")
    parser.add_argument("--silver-bucket", required=True, help="Silver zone S3 bucket name")
    parser.add_argument("--merge-key", required=True, help="Primary key for UPSERT/MERGE operations")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    
    logger.info("Starting Iceberg Ingestion Job...")
    logger.info(f"Arguments: {args}")
    
    pipeline = IcebergIngestionPipeline(
        source_path=args.source_path,
        db_name=args.db_name,
        table_name=args.table_name,
        silver_bucket=args.silver_bucket,
        merge_key=args.merge_key
    )
    
    try:
        pipeline.run()
    except Exception as e:
        logger.critical("Pipeline failed.", exc_info=True)
        sys.exit(1)