# ---------------------------------------------------------
# Shared Services: AI Metastore Catalog
# ---------------------------------------------------------
module "glue_catalog" {
  source = "../../../modules/glue_catalog"

  database_name = "${var.project}_${var.environment}_ai_catalog"
  description   = "Primary metastore for the automated data quality and cataloging agents"
}

# ---------------------------------------------------------
# Event-Driven Ingestion: Bronze S3 Drop Trigger
# ---------------------------------------------------------
module "ingest_trigger" {
  source = "../../../modules/lambda_ingest"

  function_name = "${var.project}-${var.environment}-ingest-trigger"
  environment   = var.environment
  source_dir    = "${path.module}/../../../../../src/lambda/ingest_trigger"

  # Dynamically pull the Bronze bucket name (index 0) from Phase 1 state
  trigger_bucket_name = data.terraform_remote_state.foundation.outputs.datalake_bucket_names[0]
  trigger_bucket_arn  = "arn:aws:s3:::${data.terraform_remote_state.foundation.outputs.datalake_bucket_names[0]}"
}