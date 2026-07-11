variable "bucket_prefix" {
  type        = string
  description = "Prefix for the S3 buckets (e.g., project-env-s3-region)"
}

variable "zones" {
  type        = list(string)
  description = "List of zones to create (e.g., bronze, silver, gold)"
}

variable "kms_key_arn" {
  type        = string
  description = "The ARN of the KMS key to use for server-side encryption"
}