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

output "ecs_cluster_name" {
  # Note: If your Phase 3 Terraform output for the cluster was named something 
  # else (e.g., ecs_cluster_id), change the ".ecs_cluster_name" attribute below to match.
  value       = data.terraform_remote_state.agent.outputs.ecs_cluster_name 
  description = "The exact ECS Cluster name deployed in Phase 3"
}