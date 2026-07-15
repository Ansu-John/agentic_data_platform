# Provisions the KMS key and the heavily secured S3 zones as demanded by the architecture.
module "kms" {
  source = "../../../modules/kms"

  alias_name  = "alias/${var.project}-${var.environment}-s3-key"
  description = "KMS key for ${var.environment} Data Lake S3 buckets"
}

module "s3_datalake" {
  source = "../../../modules/s3_datalake"

  bucket_prefix = "${var.project}-${var.environment}-s3-${var.aws_region}"
  zones         = var.datalake_zones
  kms_key_arn   = module.kms.key_arn # Passing the output from the KMS module as an input here
}

module "vpc" {
  source = "../../../modules/vpc"

  vpc_name    = "${var.project}-${var.environment}-vpc"
  cidr_block  = "10.0.0.0/16"
  environment = var.environment
}