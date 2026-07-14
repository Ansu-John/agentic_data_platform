output "table_arn" {
  value       = aws_dynamodb_table.langgraph_state.arn
  description = "The direct IAM resource ARN for the state persistence layer."
}

output "table_name" {
  value       = aws_dynamodb_table.langgraph_state.name
  description = "The table identifier for injection into environment variables."
}