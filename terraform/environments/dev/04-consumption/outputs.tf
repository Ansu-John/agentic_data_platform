output "consumption_endpoint" {
  value       = "http://${module.alb.alb_dns_name}"
  description = "Public URL for the Streamlit data consumption portal"
}

output "athena_workgroup_name" {
  value       = module.athena_workgroup.workgroup_name
  description = "The isolated Athena workgroup name utilized by the text-to-SQL engine"
}

output "dbt_subnet_ids" {
  value       = join(",", data.terraform_remote_state.foundation.outputs.private_subnet_ids)
  description = "Comma-separated private subnets for dbt ECS task execution"
}

output "dbt_cluster_arn" {
  # Now correctly referencing the exact variable name exported by Phase 3
  value       = data.terraform_remote_state.agent.outputs.ecs_cluster_arn
  description = "The ARN of the ECS Cluster deployed in Phase 3"
}