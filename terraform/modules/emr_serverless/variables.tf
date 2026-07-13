variable "project" {
  description = "The name of the project"
  type        = string
}

variable "environment" {
  description = "The deployment environment (e.g., dev, prod)"
  type        = string
}

variable "ecr_repository_url" {
  description = "The URL of the Amazon ECR repository containing the PySpark Docker image"
  type        = string
}

variable "subnet_ids" {
  description = "List of private subnet IDs for EMR Serverless network configuration"
  type        = list(string)
}

variable "security_group_ids" {
  description = "List of security group IDs for EMR Serverless network configuration"
  type        = list(string)
}

variable "image_tag" {
  description = "The Docker image tag to deploy to EMR Serverless (usually the Git SHA)"
  type        = string
}