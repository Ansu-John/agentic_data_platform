variable "project_name" { type = string }
variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "ecr_image_uri" { type = string }
variable "dynamodb_table_arn" { type = string }
variable "silver_bucket_arn" { type = string }
variable "environment_variables" {
  type        = map(string)
  description = "Key-value configuration maps injected into container launch parameters."
  default     = {}
}