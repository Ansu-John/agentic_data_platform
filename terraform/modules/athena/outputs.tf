output "workgroup_name" {
  value       = aws_athena_workgroup.nlq_workgroup.name
  description = "Name of the Athena Workgroup"
}

output "athena_results_bucket_arn" {
  value       = aws_s3_bucket.athena_results.arn
  description = "ARN of the S3 bucket housing Athena output data"
}