output "cluster_arn" {
  value       = aws_ecs_cluster.main.arn
  description = "The target ECS cluster execution boundary."
}

output "task_definition_arn" {
  value       = aws_ecs_task_definition.agent_task.arn
  description = "The compute definition runtime specification layout identifier."
}

output "security_group_id" {
  value       = aws_security_group.ecs_sg.id
  description = "Security firewall boundaries assigned to container runtimes."
}