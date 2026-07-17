# -------------------------------------------------------------------------
# main.tf (Cleaned up - Data blocks moved to data.tf)
# -------------------------------------------------------------------------

# 1. SNS Topic for Alerting
resource "aws_sns_topic" "dq_alerts" {
  name = "${var.project_name}-${var.environment}-dq-alerts"
}

resource "aws_sns_topic_subscription" "dq_alerts_email" {
  topic_arn = aws_sns_topic.dq_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# 2. Application Load Balancer Security Group
resource "aws_security_group" "alb_sg" {
  name        = "${var.project_name}-${var.environment}-alb-sg"
  vpc_id      = data.terraform_remote_state.foundation.outputs.vpc_id
  description = "Allow inbound HTTP traffic to the dashboard ALB"

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

# 3. ALB and Routing
resource "aws_lb" "dashboard_alb" {
  name               = "${var.project_name}-dash-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = data.terraform_remote_state.foundation.outputs.public_subnet_ids
}

resource "aws_lb_target_group" "dashboard_tg" {
  name        = "${var.project_name}-dash-tg"
  port        = 8501 # Streamlit port
  protocol    = "HTTP"
  vpc_id      = data.terraform_remote_state.foundation.outputs.vpc_id
  target_type = "ip"

  health_check {
    path                = "/_stcore/health"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
}

resource "aws_lb_listener" "dashboard_listener" {
  load_balancer_arn = aws_lb.dashboard_alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.dashboard_tg.arn
  }
}

# 4. ECS Task & Service
resource "aws_ecr_repository" "dashboard_repo" {
  name                 = "${var.project_name}-${var.environment}-dashboard"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}

output "ecr_repository_uri" {
  value = aws_ecr_repository.dashboard_repo.repository_url
}

resource "aws_cloudwatch_log_group" "dashboard_logs" {
  name              = "/ecs/${var.project_name}-${var.environment}-dashboard"
  retention_in_days = 14
}

resource "aws_ecs_task_definition" "dashboard_task" {
  family                   = "${var.project_name}-${var.environment}-dashboard"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.dashboard_execution_role.arn
  task_role_arn            = aws_iam_role.dashboard_task_role.arn

  container_definitions = jsonencode([{
    name         = "streamlit-dashboard"
    image        = "nginx:latest" # GitHub Actions will overwrite this
    essential    = true
    portMappings = [{ containerPort = 8501, hostPort = 8501 }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.dashboard_logs.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])

  lifecycle { ignore_changes = [container_definitions] }
}

resource "aws_ecs_service" "dashboard_service" {
  name            = "${var.project_name}-${var.environment}-dashboard-svc"
  cluster         = data.terraform_remote_state.agent.outputs.cluster_arn
  task_definition = aws_ecs_task_definition.dashboard_task.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.terraform_remote_state.foundation.outputs.private_subnet_ids
    security_groups  = [data.terraform_remote_state.agent.outputs.security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.dashboard_tg.arn
    container_name   = "streamlit-dashboard"
    container_port   = 8501
  }
}