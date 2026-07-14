terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(var.tags, {
      Environment = var.environment
      Project     = var.project_name
      ManagedBy   = "Terraform"
      Layer       = "Phase3-AI-Governance"
    })
  }
}