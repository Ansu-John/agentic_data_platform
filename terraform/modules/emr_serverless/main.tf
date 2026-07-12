resource "aws_emrserverless_application" "this" {
  name          = var.app_name
  release_label = "emr-7.0.0" # Use a modern EMR release for built-in Iceberg support
  type          = "SPARK"

  network_configuration {
    subnet_ids = var.private_subnet_ids
    # EMR Serverless requires a security group to communicate within the VPC
    security_group_ids = [aws_security_group.emr_sg.id]
  }

  # Define auto-start and auto-stop to save costs during development
  auto_start_configuration {
    enabled = true
  }

  auto_stop_configuration {
    enabled              = true
    idle_timeout_minutes = 15
  }

  tags = {
    Environment = var.environment
    Module      = "emr_serverless"
  }
}

resource "aws_security_group" "emr_sg" {
  name        = "${var.app_name}-sg"
  description = "Security group for EMR Serverless"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}