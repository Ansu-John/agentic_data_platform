# Task Execution Role (Allows ECS to pull images and write CloudWatch logs)
resource "aws_iam_role" "execution_role" {
  name = "${var.project_name}-${var.environment}-ecs-exec-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_policy" {
  role       = aws_iam_role.execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Task Role (Permissions for the Python LangGraph Application)
resource "aws_iam_role" "task_role" {
  name = "${var.project_name}-${var.environment}-agent-task-role"
  assume_role_policy = aws_iam_role.execution_role.assume_role_policy
}

resource "aws_iam_policy" "agent_permissions" {
  name        = "${var.project_name}-${var.environment}-agent-policy"
  description = "Permissions for AI DQ Agent to access Bedrock, Athena, Glue, and S3"
  policy      = jsonencode({
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
        Sid      = "DataLakeAccess"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = ["${var.silver_bucket_arn}/*"]
      },
      {
        Sid      = "AthenaGlueGovernance"
        Effect   = "Allow"
        Action   = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "glue:GetTable",
          "glue:UpdateTable"
        ]
        Resource = "*" # Scope down to specific catalog ARNs
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "agent_permissions_attach" {
  role       = aws_iam_role.task_role.name
  policy_arn = aws_iam_policy.agent_permissions.arn
}