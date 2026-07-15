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

variable "datalake_zones" {
  description = "List of S3 zones to create for the data lakehouse"
  type        = list(string)
  default     = ["bronze", "silver", "gold", "quarantine"]
}

variable "zones" {
  type        = list(string)
  description = "List of zones to create (e.g., bronze, silver, gold)"
  default     = ["bronze", "silver", "gold", "quarantine"]
}
