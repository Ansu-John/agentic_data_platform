variable "environment" {
  type        = string
  description = "Deployment environment"
}

variable "kms_key_arn" {
  type        = string
  description = "KMS Key ARN to encrypt query results output at rest"
}