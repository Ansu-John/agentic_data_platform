variable "aws_region" {
  type    = string
  default = "ap-south-1"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "project_name" {
  type    = string
  default = "dataplatform"
}

variable "alert_email" {
  type        = string
  description = "Email address to receive data quality alerts"
}

variable "tags" {
  type        = map(string)
  description = "Common resource tags"
}

variable "api_image_tag" {
  type        = string
  description = "Docker image tag for the FastAPI NLQ agent"
  default     = "latest"
}

variable "ui_image_tag" {
  type        = string
  description = "Docker image tag for the Streamlit UI application"
  default     = "latest"
}