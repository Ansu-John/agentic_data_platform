data "aws_caller_identity" "current" {}

# -------------------------------------------------------------------
# 1. Amazon ECR Repository for Custom Spark Image
# -------------------------------------------------------------------
resource "aws_ecr_repository" "spark_repo" {
  name                 = "${var.project}-${var.environment}-spark-jobs"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

# -------------------------------------------------------------------
# 2. IAM Execution Role for EMR Serverless
# -------------------------------------------------------------------
resource "aws_iam_role" "emr_execution_role" {
  name = "${var.project}-${var.environment}-emr-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "emr-serverless.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "emr_execution_policy" {
  name = "${var.project}-${var.environment}-emr-exec-policy"
  role = aws_iam_role.emr_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DatalakeS3Access"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:ListBucket", "s3:PutObject", "s3:DeleteObject"]
        Resource = [
          "arn:aws:s3:::dataplatform-dev-s3-aps1-bronze",
          "arn:aws:s3:::dataplatform-dev-s3-aps1-bronze/*",
          "arn:aws:s3:::dataplatform-dev-s3-aps1-silver",
          "arn:aws:s3:::dataplatform-dev-s3-aps1-silver/*"
        ]
      },
      {
        Sid      = "GlueCatalogAccess"
        Effect   = "Allow"
        Action   = ["glue:GetDatabase", "glue:CreateDatabase", "glue:GetTable", "glue:CreateTable", "glue:UpdateTable", "glue:DeleteTable", "glue:GetPartitions", "glue:BatchCreatePartition"]
        Resource = ["*"]
      }
    ]
  })
}

# -------------------------------------------------------------------
# 3. EMR Serverless Application Configuration
# -------------------------------------------------------------------
resource "aws_security_group" "emr_sg" {
  name        = "${var.project}-${var.environment}-emr-sg"
  description = "Security group for EMR Serverless Spark Application"
  vpc_id      = data.terraform_remote_state.foundation.outputs.vpc_id

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
}

resource "aws_emrserverless_application" "spark_app" {
  name          = "${var.project}-${var.environment}-spark-engine"
  release_label = "emr-7.0.0"
  type          = "SPARK"

  image_configuration {
    image_uri = "${aws_ecr_repository.spark_repo.repository_url}:latest"
  }

  network_configuration {
    subnet_ids         = data.terraform_remote_state.foundation.outputs.private_subnet_ids
    security_group_ids = [aws_security_group.emr_sg.id]
  }

  auto_start_configuration { enabled = true }
  auto_stop_configuration {
    enabled              = true
    idle_timeout_minutes = 15
  }
}

# -------------------------------------------------------------------
# 4. AWS Step Functions (The Orchestrator)
# -------------------------------------------------------------------
resource "aws_iam_role" "step_functions_role" {
  name = "${var.project}-${var.environment}-sfn-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "states.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "sfn_emr_policy" {
  name = "${var.project}-${var.environment}-sfn-emr-policy"
  role = aws_iam_role.step_functions_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["emr-serverless:StartJobRun", "emr-serverless:CancelJobRun", "emr-serverless:GetJobRun"]
        Resource = [aws_emrserverless_application.spark_app.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = [aws_iam_role.emr_execution_role.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["events:PutTargets", "events:PutRule", "events:DescribeRule"]
        Resource = ["arn:aws:events:${var.aws_region}:${data.aws_caller_identity.current.account_id}:rule/StepFunctionsGetEventForEMRServerless*"]
      }
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
          ApplicationId    = aws_emrserverless_application.spark_app.id
          ExecutionRoleArn = aws_iam_role.emr_execution_role.arn
          "Name.$"         = "$.job_name"
          JobDriver = {
            SparkSubmit = {
              EntryPoint = "local:///app/raw_to_iceberg.py"
              EntryPointArguments = [
                "--source-path", "$.source_path",
                "--db-name", "$.db_name",
                "--table-name", "$.table_name",
                "--silver-bucket", "$.silver_bucket",
                "--merge-key", "$.merge_key"
              ]
            }
          }
        }
        End = true
      }
    }
  })
}