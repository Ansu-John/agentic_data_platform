output "kms_key_arn" {
  description = "ARN of the KMS key used for S3 Data Lake encryption"
  value       = module.kms.key_arn
}

output "datalake_bucket_names" {
  description = "Map of data lake zones to their respective S3 bucket names"
  value = {
    bronze     = module.s3_datalake.bronze_bucket_name
    silver     = module.s3_datalake.silver_bucket_name
    quarantine = module.s3_datalake.quarantine_bucket_name
  }
}

output "vpc_id" {
  description = "The ID of the Foundation VPC"
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "List of private subnet IDs for EMR/ECS compute"
  value       = module.vpc.private_subnets
}