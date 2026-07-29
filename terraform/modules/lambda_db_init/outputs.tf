output "lambda_function_arn" {
  description = "The ARN of the database initialization Lambda function"
  value       = aws_lambda_function.db_init.arn
}

output "lambda_invocation_result" {
  description = "The result of the automated Terraform Lambda invocation"
  value       = aws_lambda_invocation.invoke_db_init.result
}