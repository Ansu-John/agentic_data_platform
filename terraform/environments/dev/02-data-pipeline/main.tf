provider "aws" {
  region = var.aws_region
}

# ===================================================================
# 1. CATALOG & METADATA
# ===================================================================
module "glue_catalog" {
  source = "../../../modules/glue_catalog"

  # Base tags we added earlier
  project     = var.project
  environment = var.environment

  # The missing arguments required by your module
  database_name = "${var.project}_${var.environment}_ai_catalog"
  description   = "Iceberg AI Catalog for the ${var.environment} environment"
}


module "ingest_trigger" {
  source      = "../../../modules/lambda_ingest"
  project     = var.project
  environment = var.environment
  vpc_id      = data.terraform_remote_state.foundation.outputs.vpc_id
  subnet_ids  = data.terraform_remote_state.foundation.outputs.private_subnet_ids

  function_name       = "${var.project}-${var.environment}-ingest-trigger"
  source_dir          = "../../../../src/lambda/ingest_trigger"
  trigger_bucket_name = "dataplatform-dev-s3-aps1-bronze"
  trigger_bucket_arn  = "arn:aws:s3:::dataplatform-dev-s3-aps1-bronze"

  # Inject target variables into the enterprise trigger script
  environment_variables = {
    ENVIRONMENT       = var.environment
    STEP_FUNCTION_ARN = aws_sfn_state_machine.ingestion_orchestrator.arn
    SILVER_BUCKET     = "dataplatform-dev-s3-aps1-silver"
  }
}

# -------------------------------------------------------------------
# Specialized IAM Security Boundaries for Lambda to SFN
# -------------------------------------------------------------------
resource "aws_iam_policy" "lambda_sfn_trigger_policy" {
  name        = "${var.project}-${var.environment}-lambda-sfn-trigger"
  description = "Allows the Ingestion Lambda to trigger the Step Function Orchestrator"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["states:StartExecution"]
        Resource = [data.terraform_remote_state.emr_compute.outputs.step_function_arn]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_sfn_attach" {
  role       = module.ingest_trigger.lambda_role_name
  policy_arn = aws_iam_policy.lambda_sfn_trigger_policy.arn
}

# -------------------------------------------------------------------
# S3 Event Linkage
# -------------------------------------------------------------------
resource "aws_s3_bucket_notification" "bronze_ingest_notification" {
  bucket = "dataplatform-dev-s3-aps1-bronze"

  lambda_function {
    lambda_function_arn = module.ingest_trigger.lambda_function_arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw/"
  }
}

resource "aws_lambda_permission" "allow_s3_to_call_lambda" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = module.ingest_trigger.lambda_function_name
  principal     = "s3.amazonaws.com"
  source_arn    = "arn:aws:s3:::dataplatform-dev-s3-aps1-bronze"
}