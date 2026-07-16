data "aws_caller_identity" "current" {}

# Task Execution Role (Allows ECS to pull images and write CloudWatch logs)
resource "aws_iam_role" "execution_role" {
  name = "${var.project_name}-${var.environment}-ecs-exec-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "ecs_task_athena_s3_kms_policy" {
  name = "TaskRoleAthenaFullAccess"
  role = aws_iam_role.task_role.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        # 1. Bucket Verification (Required by Athena)
        Sid    = "AthenaBucketVerification"
        Effect = "Allow"
        Action = [
          "s3:GetBucketLocation",
          "s3:ListBucket"
        ]
        Resource = [var.silver_bucket_arn]
      },
      {
        # 2. Object Access (Required for Athena Query Results)
        Sid    = "AthenaResultAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:AbortMultipartUpload"
        ]
        Resource = ["${var.silver_bucket_arn}/*"]
      },
      {
        # 3. KMS Decryption (Required if bucket is encrypted with a Customer Key)
        Sid    = "KMSAccess"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:Encrypt"
        ]
        Resource = var.kms_key_arn != null ? [var.kms_key_arn] : []
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_policy" {
  role       = aws_iam_role.execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Task Role (Permissions for the Python LangGraph Application)
resource "aws_iam_role" "task_role" {
  name               = "${var.project_name}-${var.environment}-agent-task-role"
  assume_role_policy = aws_iam_role.execution_role.assume_role_policy
}

resource "aws_iam_policy" "agent_permissions" {
  name        = "${var.project_name}-${var.environment}-agent-policy"
  description = "Permissions for AI DQ Agent to access Bedrock, Athena, Glue, and S3"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "BedrockLLM"
        Effect   = "Allow"
        Action   = ["bedrock:InvokeModel"]
        Resource = "*" # Restrict to specific Claude ARNs in production
      },
      {
        Sid      = "DynamoDBState"
        Effect   = "Allow"
        Action   = ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:UpdateItem"]
        Resource = var.dynamodb_table_arn
      },
      {
        Sid    = "DataLakeBucketAccess"
        Effect = "Allow"
        Action = [
          "s3:GetBucketLocation",
          "s3:ListBucket"
        ]
        # This points to the bucket ARN (no wildcard)
        Resource = [var.silver_bucket_arn]
      },
      {
        Sid    = "DataLakeObjectAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:AbortMultipartUpload"
        ]
        # This points to the objects inside the bucket
        Resource = ["${var.silver_bucket_arn}/*"]
      },
      {
        Sid    = "AthenaGlueGovernance"
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "glue:GetTable",
          "glue:UpdateTable"
        ]
        Resource = "*" # Scope down to specific catalog ARNs
      },
      {
        Sid    = "KMSDecryptEncrypt"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = var.kms_key_arn != null ? [var.kms_key_arn] : []
      },
      {
        Sid    = "GlueCatalogAccess"
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetPartition",
          "glue:GetPartitions",
          "glue:BatchGetPartition"
        ]
        Resource = [
          "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:catalog",
          "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:database/${var.project_name}_silver_catalog",
          "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${var.project_name}_silver_catalog/*"
        ]
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "agent_permissions_attach" {
  role       = aws_iam_role.task_role.name
  policy_arn = aws_iam_policy.agent_permissions.arn
}