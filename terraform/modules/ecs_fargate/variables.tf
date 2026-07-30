variable "project_name" { type = string }
variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "ecr_image_uri" { type = string }
variable "dynamodb_table_arn" { type = string }
variable "silver_bucket_arn" { type = string }
variable "service_name" { type = string }

# --- Optional Variables for Generic Use ---

variable "task_role_arn" {
  type        = string
  default     = null
  description = "External task role ARN. If left null, the module creates its own internal role."
}

variable "container_port" {
  type        = number
  default     = null
  description = "The port the container listens on. Leave null for background workers."
}

variable "target_group_arn" {
  type        = string
  default     = null
  description = "The ALB Target Group ARN. Leave null if not exposing via a Load Balancer."
}

variable "environment_variables" {
  type        = map(string)
  default     = {}
  description = "Key-value configuration maps injected into container launch parameters."
}

variable "kms_key_arn" {
  type        = string
  default     = null
  description = "ARN of the KMS key for S3/Athena encryption."
}

variable "aws_region" {
  type        = string
  default     = "ap-south-1"
}

variable "bedrock_model_id_prefix" {
  type        = string
  default     = "anthropic.claude*"
  description = "Foundation-model ID prefix this task role may invoke on Bedrock. Scopes bedrock:InvokeModel to a specific model family instead of Resource=\"*\"."
}

variable "athena_workgroup_name" {
  type        = string
  default     = "primary"
  description = "Athena workgroup this task role is permitted to run queries against. Scopes athena:StartQueryExecution/etc. instead of Resource=\"*\"."
}