output "application_id" {
  description = "The ID of the EMR Serverless Application"
  value       = aws_emrserverless_application.spark_app.id
}

output "application_arn" {
  description = "The ARN of the EMR Serverless Application"
  value       = aws_emrserverless_application.spark_app.arn
}

output "execution_role_arn" {
  description = "The ARN of the EMR Execution Role"
  value       = aws_iam_role.emr_execution_role.arn
}

output "step_function_arn" {
  description = "The ARN of the Ingestion Step Function Orchestrator"
  value       = aws_sfn_state_machine.ingestion_orchestrator.arn
}

output "ecr_repository_url" {
  description = "The URL of the ECR repository for PySpark images"
  value       = aws_ecr_repository.spark_repo.repository_url
}