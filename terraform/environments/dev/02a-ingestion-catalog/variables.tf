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