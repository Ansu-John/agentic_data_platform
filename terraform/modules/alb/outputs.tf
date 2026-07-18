output "alb_dns_name" {
  value       = aws_lb.external.dns_name
  description = "The public DNS name of the Ingress Load Balancer"
}

output "ui_target_group_arn" {
  value       = aws_lb_target_group.ui.arn
}

output "api_target_group_arn" {
  value       = aws_lb_target_group.api.arn
}