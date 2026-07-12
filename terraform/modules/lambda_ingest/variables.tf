variable "function_name" {
  type        = string
  description = "The name of the Lambda function"
}

variable "environment" {
  type        = string
  description = "Deployment environment"
}

variable "source_dir" {
  type        = string
  description = "Relative path to the Lambda source code directory"
}

variable "trigger_bucket_name" {
  type        = string
  description = "Name of the S3 bucket that will trigger the Lambda"
}

variable "trigger_bucket_arn" {
  type        = string
  description = "ARN of the S3 bucket that will trigger the Lambda"
}

variable "project" {
  description = "The project name"
  type        = string
}

variable "vpc_id" {
  description = "The VPC ID where the Lambda will run"
  type        = string
}

variable "subnet_ids" {
  description = "The private subnets for the Lambda"
  type        = list(string)
}

variable "environment_variables" {
  description = "A map of environment variables to inject into the Lambda"
  type        = map(string)
  default     = {}
}