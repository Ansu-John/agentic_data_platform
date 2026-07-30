# Creates a robust, highly available network topology across two Availability Zones
# Provisions a NAT Gateway for outbound internet access (needed for ECS to pull Docker images)
# Sets up the critical S3/DynamoDB gateway endpoints.

data "aws_availability_zones" "available" {
  state = "available"
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = var.vpc_name
  cidr = var.cidr_block

  # Use the first 2 Availability Zones for high availability
  azs = slice(data.aws_availability_zones.available.names, 0, 2)

  # Carve out subnets dynamically based on the VPC CIDR
  private_subnets = [for k, v in slice(data.aws_availability_zones.available.names, 0, 2) : cidrsubnet(var.cidr_block, 4, k)]
  public_subnets  = [for k, v in slice(data.aws_availability_zones.available.names, 0, 2) : cidrsubnet(var.cidr_block, 4, k + 4)]

  # Enable NAT Gateway for ECS Fargate to pull images from public internet
  enable_nat_gateway     = true
  single_nat_gateway     = var.environment == "dev" ? true : false # Save costs in Dev, use multi-NAT in Prod
  one_nat_gateway_per_az = false

  # Enable DNS hostnames (Required for EMR Serverless & Redshift)
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ---------------------------------------------------------
# VPC Gateway Endpoints for Data Lake Security & Cost Savings
# ---------------------------------------------------------
resource "aws_vpc_endpoint" "s3" {
  vpc_id          = module.vpc.vpc_id
  service_name    = "com.amazonaws.${data.aws_region.current.name}.s3"
  route_table_ids = module.vpc.private_route_table_ids

  tags = {
    Name = "${var.vpc_name}-s3-endpoint"
  }
}

resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id          = module.vpc.vpc_id
  service_name    = "com.amazonaws.${data.aws_region.current.name}.dynamodb"
  route_table_ids = module.vpc.private_route_table_ids

  tags = {
    Name = "${var.vpc_name}-dynamodb-endpoint"
  }
}

# ---------------------------------------------------------
# VPC Interface Endpoints
# ---------------------------------------------------------
# Glue, ECR, STS, CloudWatch Logs, and Bedrock Runtime calls previously had no
# private path and traversed the NAT Gateway to the public AWS API endpoints.
# These Interface Endpoints (AWS PrivateLink) keep that traffic on AWS's
# private network instead, matching the platform's private-networking
# requirement. (S3 and DynamoDB use free Gateway Endpoints above, since
# PrivateLink doesn't support Gateway-type endpoints for those services.)
resource "aws_security_group" "vpc_endpoints" {
  name        = "${var.vpc_name}-vpce-sg"
  description = "Allows HTTPS from within the VPC to Interface VPC Endpoints"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description = "HTTPS from the VPC CIDR"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.vpc_name}-vpce-sg"
  }
}

locals {
  interface_endpoint_services = {
    glue           = "glue"
    ecr_api        = "ecr.api"
    ecr_dkr        = "ecr.dkr"
    sts            = "sts"
    logs           = "logs"
    bedrock_runtime = "bedrock-runtime"
  }
}

resource "aws_vpc_endpoint" "interface_endpoints" {
  for_each = local.interface_endpoint_services

  vpc_id              = module.vpc.vpc_id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.${each.value}"
  vpc_endpoint_type    = "Interface"
  subnet_ids           = module.vpc.private_subnets
  security_group_ids   = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled  = true

  tags = {
    Name = "${var.vpc_name}-${each.key}-endpoint"
  }
}

data "aws_region" "current" {}