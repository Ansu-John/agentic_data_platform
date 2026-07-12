terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket         = "dataplatform-dev-tfstate-bucket"
    key            = "dev/02a-ingestion-catalog/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "ai-catalog-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
}

# -------------------------------------------------------------------
# Data Sources & Cross-Phase State Wiring
# -------------------------------------------------------------------
data "terraform_remote_state" "foundation" {
  backend = "s3"
  config = {
    bucket = "dataplatform-dev-tfstate-bucket"
    key    = "dev/01-foundation/terraform.tfstate"
    region = var.aws_region
  }
}

data "terraform_remote_state" "emr_compute" {
  backend = "s3"
  config = {
    bucket = "dataplatform-dev-tfstate-bucket"
    key    = "dev/02b-emr-compute/terraform.tfstate"
    region = var.aws_region
  }
}

# -------------------------------------------------------------------
# Modules
# -------------------------------------------------------------------
module "glue_catalog" {
  source      = "../../../modules/glue_catalog"
  project     = var.project
  environment = var.environment
}

module "ingest_trigger" {
  source      = "../../../modules/lambda_ingest"
  project     = var.project
  environment = var.environment
  vpc_id      = data.terraform_remote_state.foundation.outputs.vpc_id
  subnet_ids  = data.terraform_remote_state.foundation.outputs.private_subnet_ids

  # Inject target variables into the enterprise trigger script
  environment_variables = {
    ENVIRONMENT       = var.environment
    STEP_FUNCTION_ARN = data.terraform_remote_state.emr_compute.outputs.step_function_arn
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