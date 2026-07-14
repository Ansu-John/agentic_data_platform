variable "aws_region" {
  type        = string
  description = "The target AWS Region for deployment."
  default     = "ap-south-1"
}

variable "environment" {
  type        = string
  description = "Deployment environment namespace."
  default     = "dev"
}

variable "project_name" {
  type        = string
  description = "Core name identifier for the enterprise platform."
  default     = "dataplatform"
}

variable "terraform_state_bucket" {
  type        = string
  description = "S3 bucket housing remote state files for cross-layer references."
  default     = "dataplatform-dev-terraform-state"
}

variable "agent_ecr_image_uri" {
  type        = string
  description = "Fully qualified ECR Docker image URI containing the LangGraph application."
}

variable "tags" {
  type        = map(string)
  description = "Resource metadata tag map."
  default     = {}
}