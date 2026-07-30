variable "aws_region" {
  description = "The AWS region to deploy resources into"
  type        = string
}

variable "environment" {
  description = "The deployment environment (e.g., dev, stage, prod)"
  type        = string
}

variable "project" {
  description = "The overarching project name for resource tagging and naming"
  type        = string
}

variable "image_tag" {
  description = "The Docker image tag deployed from GitHub Actions"
  type        = string
}

variable "source_code_path" {
  description = "The absolute path to the Lambda zip file, injected by GitHub Actions"
  type        = string
  default     = "" # Prevents local runs from crashing if not provided
}