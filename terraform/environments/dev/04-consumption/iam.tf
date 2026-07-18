# Execution and Task Roles for the NLQ Execution Service
resource "aws_iam_role" "nlq_task_role" {
  name = "dataplatform-${var.environment}-nlq-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_policy" "nlq_execution_policy" {
  name        = "dataplatform-${var.environment}-nlq-execution-policy"
  description = "Least privilege access for Phase 4 NLQ engine to query Athena, Glue, and Bedrock"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Bedrock foundation model invocation
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/*"
      },
      # Athena Query Execution Permissions
      {
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:StopQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults"
        ]
        Resource = "*"
      },
      # Read-only access to Glue Catalog metadata enriched in Phase 3
      {
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetTable",
          "glue:GetDatabases",
          "glue:GetDatabase",
          "glue:GetTables",
          "glue:GetPartitions"
        ]
        Resource = [
          "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:catalog",
          "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:database/dataplatform_${var.environment}_ai_catalog",
          "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/dataplatform_${var.environment}_ai_catalog/*"
        ]
      },
      # Read-only access to Silver/Gold Iceberg S3 data layer, Read/Write to Athena Results
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          data.terraform_remote_state.data_pipeline.outputs.silver_bucket_arn,
          "${data.terraform_remote_state.data_pipeline.outputs.silver_bucket_arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetBucketLocation",
          "s3:GetObject",
          "s3:ListBucket",
          "s3:PutObject"
        ]
        Resource = [
          module.athena_workgroup.athena_results_bucket_arn,
          "${module.athena_workgroup.athena_results_bucket_arn}/*"
        ]
      },
      # KMS Decryption for S3/Glue data
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = [data.terraform_remote_state.data_pipeline.outputs.kms_key_arn]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "nlq_attach" {
  role       = aws_iam_role.nlq_task_role.name
  policy_arn = aws_iam_policy.nlq_execution_policy.arn
}