output "key_arn" {
  value       = aws_kms_key.this.arn
  description = "The ARN of the KMS key"
}