resource "aws_dynamodb_table" "langgraph_state" {
  name         = var.table_name
  billing_mode = var.billing_mode

  # Key schema matches the "langgraph-checkpoint-aws" DynamoDBSaver's unified
  # single-table design: it encodes thread_id/checkpoint_ns/checkpoint_id/write
  # ordering into composite PK/SK string values itself (queried via
  # `KeyConditionExpression: "PK = :pk"`), rather than exposing thread_id and
  # checkpoint_ns as separate top-level attributes. See
  # src/agent/graph.py and src/api/agents/nlq_agent/graph.py.
  hash_key  = "PK"
  range_key = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  # The DynamoDBSaver writes an epoch-seconds "ttl" attribute when constructed
  # with ttl_seconds set, so DynamoDB can auto-expire old checkpoints/writes.
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = var.tags
}