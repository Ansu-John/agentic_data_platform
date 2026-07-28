# 1. Isolated Athena Workgroup for NLQ execution governance
module "athena_workgroup" {
  source      = "../../../modules/athena"
  environment = var.environment
  kms_key_arn = data.terraform_remote_state.foundation.outputs.kms_key_arn
}

# 2. Public Ingress Ingress Load Balancer for routing API and UI traffic
module "alb" {
  source             = "../../../modules/alb"
  environment        = var.environment
  vpc_id             = data.terraform_remote_state.foundation.outputs.vpc_id
  public_subnets     = data.terraform_remote_state.foundation.outputs.private_subnet_ids
  security_group_ids = [data.terraform_remote_state.foundation.outputs.alb_security_group_id]
}

module "dynamodb_checkpoints" {
  source       = "../../../modules/dynamodb_state"
  table_name   = "langgraph-checkpoints-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  tags         = var.tags
}

# Create ECR Repository for the NLQ API
resource "aws_ecr_repository" "api_repo" {
  name                 = "${var.project_name}-${var.environment}-nlq-api"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}

# Create ECR Repository for the Streamlit UI
resource "aws_ecr_repository" "ui_repo" {
  name                 = "${var.project_name}-${var.environment}-streamlit-ui"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}

# 3. Deploy the FastAPI NLQ Backend Service via your generic ECS module
module "ecs_nlq_api" {
  source             = "../../../modules/ecs_fargate"
  service_name       = "nlq-api"
  environment        = var.environment
  vpc_id             = data.terraform_remote_state.foundation.outputs.vpc_id
  private_subnet_ids = data.terraform_remote_state.foundation.outputs.private_subnet_ids
  task_role_arn      = aws_iam_role.nlq_task_role.arn
  container_port     = 8000
  target_group_arn   = module.alb.api_target_group_arn
  
  project_name       = var.project_name 
  ecr_image_uri      = "${aws_ecr_repository.api_repo.repository_url}:${var.api_image_tag}"
  dynamodb_table_arn = module.dynamodb_checkpoints.table_arn
  silver_bucket_arn  =  "arn:aws:s3:::${data.terraform_remote_state.foundation.outputs.datalake_bucket_names["silver"]}"
  
  # Inject variables specific to runtime configurations
  environment_variables = {
    ENVIRONMENT      = var.environment
    ATHENA_WORKGROUP = module.athena_workgroup.workgroup_name
    GLUE_DATABASE    = "dataplatform_${var.environment}_ai_catalog"
  }
}

# 4. Deploy the Streamlit Interface via your generic ECS module
module "ecs_streamlit_ui" {
  source             = "../../../modules/ecs_fargate"
  service_name       = "streamlit-ui"
  environment        = var.environment
  vpc_id             = data.terraform_remote_state.foundation.outputs.vpc_id
  private_subnet_ids = data.terraform_remote_state.foundation.outputs.private_subnet_ids
  task_role_arn      = aws_iam_role.nlq_task_role.arn # Streamlit task role can inherit or use standard
  container_port     = 8501
  target_group_arn   = module.alb.ui_target_group_arn

  project_name       = var.project_name 
  ecr_image_uri      = "${aws_ecr_repository.ui_repo.repository_url}:${var.ui_image_tag}"
  dynamodb_table_arn = module.dynamodb_checkpoints.table_arn
  silver_bucket_arn  =  "arn:aws:s3:::${data.terraform_remote_state.foundation.outputs.datalake_bucket_names["silver"]}"
  
  environment_variables = {
    API_URL = "http://${module.alb.alb_dns_name}/api/v1"
  }
}

# Restored ALB Security Group
resource "aws_security_group" "alb_sg" {
  name        = "${var.project_name}-${var.environment}-alb-sg"
  description = "Allow inbound HTTP traffic to the dashboard ALB"
  vpc_id      = data.terraform_remote_state.foundation.outputs.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# 2. Public Ingress Load Balancer for routing API and UI traffic
module "alb" {
  source             = "../../../modules/alb"
  environment        = var.environment
  vpc_id             = data.terraform_remote_state.foundation.outputs.vpc_id
  
  # Ensure this points to public_subnet_ids
  public_subnets     = data.terraform_remote_state.foundation.outputs.private_subnet_ids 
  
  # THIS IS THE CRITICAL FIX FOR LINE 14:
  security_group_ids = [data.terraform_remote_state.agent.outputs.security_group_id]
}