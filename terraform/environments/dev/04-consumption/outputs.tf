output "consumption_endpoint" {
  value       = "http://${module.alb.alb_dns_name}"
  description = "Public URL for the Streamlit data consumption portal"
}

output "athena_workgroup_name" {
  value       = module.athena_workgroup.workgroup_name
  description = "The isolated Athena workgroup name utilized by the text-to-SQL engine"
}