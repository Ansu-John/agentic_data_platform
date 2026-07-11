output "database_name" {
  value       = aws_glue_catalog_database.this.name
  description = "The name of the created Glue database"
}

output "database_arn" {
  value       = aws_glue_catalog_database.this.arn
  description = "The ARN of the created Glue database"
}