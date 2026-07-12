output "application_id" {
  description = "The ID of the EMR Serverless Application"
  value       = aws_emrserverless_application.this.id
}

output "application_arn" {
  description = "The ARN of the EMR Serverless Application"
  value       = aws_emrserverless_application.this.arn
}