# ===================================================================
# 1. ECR & EMR COMPUTE OUTPUTS
# ===================================================================
output "ecr_repository_url" {
  description = "The URL of the ECR repository for PySpark container images"
  value       = aws_ecr_repository.spark_repo.repository_url
}

output "emr_application_id" {
  description = "The ID of the EMR Serverless Spark Application"
  value       = module.emr_serverless.application_id
}
output "emr_application_arn" {
  description = "The ARN of the EMR Serverless Spark Application"
  value       = module.emr_serverless.application_arn
}

output "emr_execution_role_arn" {
  description = "The ARN of the IAM Execution Role used by EMR Serverless"
  value       = aws_iam_role.emr_execution_role.arn
}

# ===================================================================
# 2. ORCHESTRATION OUTPUTS
# ===================================================================
output "step_function_arn" {
  description = "The ARN of the Data Ingestion Step Function Orchestrator"
  value       = aws_sfn_state_machine.ingestion_orchestrator.arn
}

# ===================================================================
# 3. INGESTION & TRIGGER OUTPUTS
# ===================================================================
output "lambda_trigger_arn" {
  description = "The ARN of the S3-triggered Lambda function"
  value       = module.ingest_trigger.lambda_function_arn
}

output "lambda_trigger_name" {
  description = "The name of the S3-triggered Lambda function"
  value       = module.ingest_trigger.lambda_function_name
}
