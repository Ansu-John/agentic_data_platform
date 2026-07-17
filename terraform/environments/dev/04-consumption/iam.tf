# Task Execution Role (Pulling images, writing logs)
resource "aws_iam_role" "dashboard_execution_role" {
  name = "${var.project_name}-${var.environment}-dashboard-exec-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "exec_policy_attachment" {
  role       = aws_iam_role.dashboard_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Task Role (App permissions: Athena, Glue, S3)
resource "aws_iam_role" "dashboard_task_role" {
  name               = "${var.project_name}-${var.environment}-dashboard-task-role"
  assume_role_policy = aws_iam_role.dashboard_execution_role.assume_role_policy
}

resource "aws_iam_policy" "dashboard_permissions" {
  name = "${var.project_name}-${var.environment}-dashboard-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "glue:GetTable",
          "glue:GetDatabases",
          "glue:GetTables",
          "glue:GetDatabase"
        ]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:ListBucket", "s3:GetBucketLocation"]
        Resource = ["*"] # Scope this down to your Silver/Athena output buckets in Prod
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "task_policy_attachment" {
  role       = aws_iam_role.dashboard_task_role.name
  policy_arn = aws_iam_policy.dashboard_permissions.arn
}