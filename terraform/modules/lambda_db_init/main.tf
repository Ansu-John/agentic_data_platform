data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = var.source_code_path
  output_path = "${path.module}/init_db.zip"
}

resource "aws_iam_role" "lambda_role" {
  name = "dataplatform-dev-db-init-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17", Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  role = aws_iam_role.lambda_role.name
  policy = jsonencode({
    Version = "2012-10-17", Statement = [
      { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = var.secret_arn },
      { Effect = "Allow", Action = ["ec2:CreateNetworkInterface", "ec2:DescribeNetworkInterfaces", "ec2:DeleteNetworkInterface"], Resource = "*" },
      { Effect = "Allow", Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], Resource = "*" }
    ]
  })
}

resource "aws_lambda_function" "db_init" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "dataplatform-dev-db-init"
  role             = aws_iam_role.lambda_role.arn
  
  handler          = "init_db.lambda_handler" 
  
  runtime          = "python3.11"
  timeout          = 60
  
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  
  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [var.security_group_id]
  }

  environment {
    variables = {
      DB_HOST    = var.cluster_endpoint
      DB_NAME    = var.database_name
      SECRET_ARN = var.secret_arn
    }
  }
}

# This forces Terraform to INVOKE the Lambda immediately after creating it
resource "aws_lambda_invocation" "invoke_db_init" {
  function_name = aws_lambda_function.db_init.function_name
  input         = jsonencode({ "trigger" : "terraform_apply" })
  depends_on    = [aws_lambda_function.db_init]
}