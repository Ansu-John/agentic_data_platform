resource "aws_emrserverless_application" "this" {
  name          = "${var.project}-${var.environment}-spark-engine"
  release_label = "emr-7.0.0"
  type          = "SPARK"

  # Let Terraform dynamically manage the tag
  image_configuration {
    image_uri = "${var.ecr_repository_url}:${var.image_tag}"
  }

  network_configuration {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }

  auto_start_configuration {
    enabled = true
  }

  auto_stop_configuration {
    enabled              = true
    idle_timeout_minutes = 15
  }
}