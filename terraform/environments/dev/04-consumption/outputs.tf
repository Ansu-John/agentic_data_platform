output "dashboard_url" {
  value       = "http://${aws_lb.dashboard_alb.dns_name}"
  description = "The public URL to access the Data Discovery Dashboard"
}

output "sns_topic_arn" {
  value       = aws_sns_topic.dq_alerts.arn
  description = "The ARN of the SNS topic for Data Quality alerts"
}