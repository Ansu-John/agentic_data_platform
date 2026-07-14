output "rule_arn" {
  value       = aws_cloudwatch_event_rule.step_function_complete.arn
  description = "The absolute ARN boundary defining the pipeline listener mechanism."
}