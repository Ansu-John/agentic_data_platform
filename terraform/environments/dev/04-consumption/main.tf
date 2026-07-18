# 1. Isolated Athena Workgroup for NLQ execution governance
module "athena_workgroup" {
  source      = "../../modules/athena"
  environment = var.environment
  kms_key_arn = data.terraform_remote_state.data_pipeline.outputs.kms_key_arn
}

# 2. Public Ingress Ingress Load Balancer for routing API and UI traffic
module "alb" {
  source             = "../../modules/alb"
  environment        = var.environment
  vpc_id             = data.terraform_remote_state.data_pipeline.outputs.vpc_id
  public_subnets     = data.terraform_remote_state.data_pipeline.outputs.public_subnets
  security_group_ids = [data.terraform_remote_state.data_pipeline.outputs.alb_security_group_id]
}

# 3. Deploy the FastAPI NLQ Backend Service via your generic ECS module
module "ecs_nlq_api" {
  source             = "../../modules/ecs_fargate"
  service_name       = "nlq-api"
  environment        = var.environment
  vpc_id             = data.terraform_remote_state.data_pipeline.outputs.vpc_id
  private_subnets    = data.terraform_remote_state.data_pipeline.outputs.private_subnets
  task_role_arn      = aws_iam_role.nlq_task_role.arn
  container_port     = 8000
  target_group_arn   = module.alb.api_target_group_arn
  
  # Inject variables specific to runtime configurations
  environment_variables = [
    { name = "ENVIRONMENT", value = var.environment },
    { name = "ATHENA_WORKGROUP", value = module.athena_workgroup.workgroup_name },
    { name = "GLUE_DATABASE", value = "dataplatform_${var.environment}_ai_catalog" }
  ]
}

# 4. Deploy the Streamlit Interface via your generic ECS module
module "ecs_streamlit_ui" {
  source             = "../../modules/ecs_fargate"
  service_name       = "streamlit-ui"
  environment        = var.environment
  vpc_id             = data.terraform_remote_state.data_pipeline.outputs.vpc_id
  private_subnets    = data.terraform_remote_state.data_pipeline.outputs.private_subnets
  task_role_arn      = aws_iam_role.nlq_task_role.arn # Streamlit task role can inherit or use standard
  container_port     = 8501
  target_group_arn   = module.alb.ui_target_group_arn

  environment_variables = [
    { name = "API_URL", value = "http://${module.alb.alb_dns_name}/api/v1" }
  ]
}