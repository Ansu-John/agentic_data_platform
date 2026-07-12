variable "database_name" {
  type        = string
  description = "The name of the Glue Catalog database"
}

variable "description" {
  type        = string
  description = "Description of the Glue Catalog database"
  default     = "Central metastore for the data platform"
}

variable "project" {
  description = "The project name"
  type        = string
}

variable "environment" {
  description = "The environment (e.g., dev, prod)"
  type        = string
}