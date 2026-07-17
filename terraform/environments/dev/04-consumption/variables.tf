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