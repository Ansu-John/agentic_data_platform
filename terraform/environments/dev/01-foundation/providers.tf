# Configure AWS and set up default tags so every resource inherits cost-allocation tags.

terraform {
  required_version = ">= 1.5.0"
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
    tags = {
      Environment = "dev"
      Project     = "ModernDataPlatform"
      ManagedBy   = "Terraform"
      Layer       = "01-foundation"
    }
  }
}