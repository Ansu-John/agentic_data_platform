data "aws_region" "current" {}

resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-${var.environment}-ai-cluster"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_cloudwatch_log_group" "agent_logs" {
  name              = "/ecs/${var.project_name}-${var.environment}-dq-agent"
  retention_in_days = 30
}

resource "aws_ecs_task_definition" "agent_task" {
  family                   = "${var.project_name}-${var.environment}-dq-agent"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.execution_role.arn
  task_role_arn            = aws_iam_role.task_role.arn

  container_definitions = jsonencode([{
    name      = "dq-agent"
    image     = var.ecr_image_uri
    essential = true
    
    environment = [
      for k, v in var.environment_variables : { name = k, value = v }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.agent_logs.name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
  lifecycle {
    ignore_changes = [
      container_definitions
    ]
  }
}

resource "aws_security_group" "ecs_sg" {
  name        = "${var.project_name}-${var.environment}-ecs-agent-sg"
  vpc_id      = var.vpc_id
  description = "Isolates outbound network execution layers for Fargate agent containers."

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
}