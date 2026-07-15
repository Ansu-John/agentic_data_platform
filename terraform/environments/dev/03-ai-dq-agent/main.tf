locals {
  vpc_id             = data.terraform_remote_state.foundation.outputs.vpc_id
  private_subnet_ids = data.terraform_remote_state.foundation.outputs.private_subnet_ids
  step_function_arn  = data.terraform_remote_state.data_pipeline.outputs.step_function_arn
}

module "dynamodb_checkpoints" {
  source       = "../../../modules/dynamodb_state"
  table_name   = "langgraph-checkpoints-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  tags         = var.tags
}

module "ai_dq_agent_compute" {
  source             = "../../../modules/ecs_fargate"
  project_name       = var.project_name
  environment        = var.environment
  vpc_id             = local.vpc_id
  private_subnet_ids = local.private_subnet_ids
  ecr_image_uri      = var.agent_ecr_image_uri
  dynamodb_table_arn = module.dynamodb_checkpoints.table_arn
  silver_bucket_arn  = "arn:aws:s3:::${data.terraform_remote_state.foundation.outputs.datalake_bucket_names["silver"]}"

  # Injecting environment variables into the container
  environment_variables = {
    ENVIRONMENT            = var.environment
    AWS_REGION             = var.aws_region
    SILVER_BUCKET_NAME     = data.terraform_remote_state.foundation.outputs.datalake_bucket_names["silver"]
    QUARANTINE_BUCKET_NAME = data.terraform_remote_state.foundation.outputs.datalake_bucket_names["quarantine"]
  }
}

module "eventbridge_trigger" {
  source                  = "../../../modules/eventbridge_ecs_trigger"
  project_name            = var.project_name
  environment             = var.environment
  step_function_arn       = local.step_function_arn
  ecs_cluster_arn         = module.ai_dq_agent_compute.cluster_arn
  ecs_task_definition_arn = module.ai_dq_agent_compute.task_definition_arn
  private_subnet_ids      = local.private_subnet_ids
  ecs_security_group_id   = module.ai_dq_agent_compute.security_group_id
}