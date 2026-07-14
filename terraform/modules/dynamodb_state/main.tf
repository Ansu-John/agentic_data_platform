resource "aws_dynamodb_table" "langgraph_state" {
  name         = var.table_name
  billing_mode = var.billing_mode
  hash_key     = "thread_id"
  range_key    = "checkpoint_ns"

  attribute {
    name = "thread_id"
    type = "S"
  }

  attribute {
    name = "checkpoint_ns"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = var.tags
}