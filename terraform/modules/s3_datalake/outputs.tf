output "bucket_names" {
  value       = aws_s3_bucket.datalake_zones[*].bucket
  description = "List of created S3 bucket names"
}