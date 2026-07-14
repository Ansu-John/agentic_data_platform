variable "table_name" {
  type        = string
  description = "The unique name for the DynamoDB state checkpointer table."
}

variable "billing_mode" {
  type        = string
  description = "Controls capacity billing layout (PROVISIONED or PAY_PER_REQUEST)."
  default     = "PAY_PER_REQUEST"
}

variable "tags" {
  type        = map(string)
  description = "Module specific tag mappings."
  default     = {}
}