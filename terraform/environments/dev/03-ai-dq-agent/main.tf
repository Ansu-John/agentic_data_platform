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
  kms_key_arn        = data.terraform_remote_state.foundation.outputs.kms_key_arn 

  service_name = "ai_dq_agent"
  #task_role_arn      = aws_iam_role.task_role.arn
  container_port     = 8201
  #target_group_arn   = module.ecs_fargate.target_group_arn

  # Injecting environment variables into the container
  environment_variables = {
    ENVIRONMENT            = var.environment
    AWS_REGION             = var.aws_region
    SILVER_BUCKET_NAME     = data.terraform_remote_state.foundation.outputs.datalake_bucket_names["silver"]
    QUARANTINE_BUCKET_NAME = data.terraform_remote_state.foundation.outputs.datalake_bucket_names["quarantine"]
    ATHENA_WORKGROUP       = "primary"
  }
}
# ==============================================================================
# EVENTBRIDGE TRIGGER (PHASE 2 -> PHASE 3 HANDOFF)
# ==============================================================================
# This is now the ONLY EventBridge rule/target wiring this hand-off. A second,
# near-identical hand-rolled aws_cloudwatch_event_rule/aws_cloudwatch_event_target
# block used to live here alongside this module call -- both listened for the
# same Step Functions SUCCEEDED event and both invoked ecs:RunTask against the
# same agent, double-triggering it on every successful pipeline run. Removed;
# this module instantiation is the single source of truth for the trigger.
#
# Known follow-up (not in this change): modules/eventbridge_ecs_trigger's own
# iam:PassRole grant (in modules/eventbridge_ecs_trigger/main.tf) is still
# Resource="*" (narrowed only by an iam:PassedToService condition), not scoped
# to this agent's specific task/execution roles the way Batch 1 scoped the
# now-removed duplicate's PassRole. Worth tightening in a later pass.
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
