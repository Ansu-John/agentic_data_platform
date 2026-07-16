output "ecs_cluster_arn" {
  value       = module.ai_dq_agent_compute.cluster_arn
  description = "The ARN of the Phase 3 ECS cluster."
}

output "dynamodb_checkpoint_table_name" {
  value       = module.dynamodb_checkpoints.table_name
  description = "DynamoDB table name utilized for LangGraph state persistence."
}

output "eventbridge_rule_arn" {
  value       = module.eventbridge_trigger.rule_arn
  description = "The EventBridge rule ARN triggering the Fargate multi-agent task."
}
