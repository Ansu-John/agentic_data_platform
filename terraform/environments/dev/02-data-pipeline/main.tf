provider "aws" { region = var.aws_region }

# ===================================================================
# 1. CATALOG & METADATA
# ===================================================================
module "glue_catalog" {
  source        = "../../../modules/glue_catalog"
  project       = var.project
  environment   = var.environment
  database_name = "${var.project}_${var.environment}_ai_catalog"
  description   = "Iceberg AI Catalog for the ${var.environment} environment"
}

# ===================================================================
# 2. ECR & EMR SERVERLESS COMPUTE
# ===================================================================
resource "aws_ecr_repository" "spark_repo" {
  name                 = "${var.project}-${var.environment}-spark-jobs"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}

# AI DQ Agent Repo for Phase 3
resource "aws_ecr_repository" "dq_agent_repo" {
  name                 = "dataplatform-ai-dq-agent" # Hardcoded to match Phase 3 workflow env var
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository_policy" "emr_ecr_policy" {
  repository = aws_ecr_repository.spark_repo.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowEMRServerlessAccess"
        Effect = "Allow"
        Principal = {
          Service = "emr-serverless.amazonaws.com"
        }
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:DescribeImages",
          "ecr:GetDownloadUrlForLayer"
        ]
      }
    ]
  })
}

resource "aws_security_group" "emr_sg" {
  name   = "${var.project}-${var.environment}-emr-sg"
  vpc_id = data.terraform_remote_state.foundation.outputs.vpc_id
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

module "emr_serverless" {
  source             = "../../../modules/emr_serverless"
  project            = var.project
  environment        = var.environment
  ecr_repository_url = aws_ecr_repository.spark_repo.repository_url
  subnet_ids         = data.terraform_remote_state.foundation.outputs.private_subnet_ids
  security_group_ids = [aws_security_group.emr_sg.id]
  # Pass the root variable down into the module
  image_tag = var.image_tag
}

resource "aws_iam_role" "emr_execution_role" {
  name = "${var.project}-${var.environment}-emr-exec-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17", Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "emr-serverless.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy" "emr_execution_policy" {
  name = "${var.project}-${var.environment}-emr-exec-policy"
  role = aws_iam_role.emr_execution_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        "Sid" : "BucketLevelList",
        "Action" : [
          "s3:ListBucket"
        ],
        "Effect" : "Allow",
        "Resource" : [
          "arn:aws:s3:::dataplatform-dev-s3-ap-south-1-bronze",
          "arn:aws:s3:::dataplatform-dev-s3-ap-south-1-silver"
        ]
      },
      {
        "Sid" : "ObjectLevelReadWrite",
        "Action" : [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ],
        "Effect" : "Allow",
        "Resource" : [
          "arn:aws:s3:::dataplatform-dev-s3-ap-south-1-bronze/*",
          "arn:aws:s3:::dataplatform-dev-s3-ap-south-1-silver/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:CreateDatabase",
          "glue:GetTable",
          "glue:CreateTable",
          "glue:UpdateTable",
          "glue:GetPartitions",
        "glue:BatchCreatePartition"]
        Resource = ["*"]
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:DescribeImages"
        ]
        Resource = ["*"]
      },
      {
        Sid = "KMSAccess",
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ],
        Effect = "Allow",
        Resource = [
          data.aws_kms_alias.s3_kms_key.target_key_arn
        ]
      }
    ]
  })
}

# ===================================================================
# 3. STEP FUNCTIONS ORCHESTRATOR
# ===================================================================
resource "aws_iam_role" "step_functions_role" {
  name = "${var.project}-${var.environment}-sfn-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17", Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "states.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy" "sfn_emr_policy" {
  name = "${var.project}-${var.environment}-sfn-emr-policy"
  role = aws_iam_role.step_functions_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["emr-serverless:StartJobRun", "emr-serverless:CancelJobRun", "emr-serverless:GetJobRun"], Resource = [module.emr_serverless.application_arn, "${module.emr_serverless.application_arn}/jobruns/*"] },
      { Effect = "Allow", Action = ["iam:PassRole"], Resource = [aws_iam_role.emr_execution_role.arn] },
      { Effect = "Allow", Action = ["events:PutTargets", "events:PutRule", "events:DescribeRule"], Resource = ["arn:aws:events:${var.aws_region}:${data.aws_caller_identity.current.account_id}:rule/StepFunctions*"] }
    ]
  })
}

resource "aws_sfn_state_machine" "ingestion_orchestrator" {
  name     = "${var.project}-${var.environment}-ingestion-pipeline"
  role_arn = aws_iam_role.step_functions_role.arn
  definition = jsonencode({
    Comment = "Orchestrates S3 Bronze to Silver Iceberg Ingestion using Dockerized Spark"
    StartAt = "RunSparkIngestion"
    States = {
      RunSparkIngestion = {
        Type     = "Task"
        Resource = "arn:aws:states:::emr-serverless:startJobRun.sync"
        Parameters = {
          ApplicationId    = module.emr_serverless.application_id
          ExecutionRoleArn = aws_iam_role.emr_execution_role.arn
          "Name.$"         = "$.job_name"
          JobDriver = {
            SparkSubmit = {
              EntryPoint              = "local:///home/hadoop/raw_to_iceberg.py"
              "EntryPointArguments.$" = "States.Array('--source-path', $.source_path, '--db-name', $.db_name, '--table-name', $.table_name, '--silver-bucket', $.silver_bucket, '--merge-key', $.merge_key)"
            }
          }
        }
        End = true
      }
    }
  })
}

# ===================================================================
# 4. LAMBDA INGESTION TRIGGER
# ===================================================================
module "ingest_trigger" {
  source      = "../../../modules/lambda_ingest"
  project     = var.project
  environment = var.environment
  vpc_id      = data.terraform_remote_state.foundation.outputs.vpc_id
  subnet_ids  = data.terraform_remote_state.foundation.outputs.private_subnet_ids

  function_name       = "${var.project}-${var.environment}-ingest-trigger"
  source_dir          = "../../../../src/lambda/ingest_trigger"
  trigger_bucket_name = "dataplatform-dev-s3-ap-south-1-bronze"
  trigger_bucket_arn  = "arn:aws:s3:::dataplatform-dev-s3-ap-south-1-bronze"

  environment_variables = {
    ENVIRONMENT       = var.environment
    STEP_FUNCTION_ARN = aws_sfn_state_machine.ingestion_orchestrator.arn
    SILVER_BUCKET     = "dataplatform-dev-s3-ap-south-1-silver"
  }
}

resource "aws_iam_role_policy_attachment" "lambda_sfn_attach" {
  role       = module.ingest_trigger.lambda_role_name
  policy_arn = aws_iam_policy.lambda_sfn_trigger_policy.arn
}

resource "aws_iam_policy" "lambda_sfn_trigger_policy" {
  name = "${var.project}-${var.environment}-lambda-sfn-trigger"
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = ["states:StartExecution"], Resource = [aws_sfn_state_machine.ingestion_orchestrator.arn] }]
  })
}

resource "aws_s3_bucket_notification" "bronze_ingest_notification" { # Note: Ensure this bucket name matches exactly what you created!
  bucket = "dataplatform-dev-s3-ap-south-1-bronze"

  lambda_function {
    lambda_function_arn = module.ingest_trigger.lambda_function_arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw/"
  }

  # THE MAGIC FIX: Forces Terraform to wait for the Lambda permissions to attach
  depends_on = [module.ingest_trigger]
}