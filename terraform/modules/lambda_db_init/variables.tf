variable "vpc_id" {
  type        = string
  description = "VPC ID where the Lambda function will be deployed"
}

variable "subnet_ids" {
  type        = list(string)
  description = "List of private subnet IDs for Lambda VPC attachment"
}

variable "security_group_id" {
  type        = string
  description = "Security Group ID allowing outbound access to Aurora PostgreSQL"
}

variable "cluster_endpoint" {
  type        = string
  description = "The write endpoint of the Aurora PostgreSQL cluster"
}

variable "database_name" {
  type        = string
  description = "Target database name to initialize"
}

variable "secret_arn" {
  type        = string
  description = "ARN of the AWS Secrets Manager secret containing DB credentials"
}

variable "source_code_path" {
  type        = string
  description = "Absolute or relative path to the Python source code directory (e.g., ../../../src/db)"
}