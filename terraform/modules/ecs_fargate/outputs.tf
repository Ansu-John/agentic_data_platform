output "cluster_arn" {
  value       = aws_ecs_cluster.main.arn
  description = "The target ECS cluster execution boundary."
}

output "task_definition_arn" {
  value       = replace(aws_ecs_task_definition.service_task.arn, "/:\\d+$/", "") # strip the revision in Terraform so EventBridge Target inside Terraform points to the Task Definition Family ARN (without the :revision_number at the end).
  description = "The compute definition runtime specification layout identifier."
}

output "security_group_id" {
  value       = aws_security_group.ecs_sg.id
  description = "Security firewall boundaries assigned to container runtimes."
}

output "task_role_arn" {
  value       = aws_iam_role.task_role.arn
  description = "ARN of the internally-created ECS task role. Needed by callers (e.g. EventBridge invoke roles) to scope iam:PassRole to this specific role instead of Resource=\"*\"."
}

output "execution_role_arn" {
  value       = aws_iam_role.execution_role.arn
  description = "ARN of the ECS task execution role, for the same PassRole-scoping purpose."
}