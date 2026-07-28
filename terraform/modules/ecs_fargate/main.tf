data "aws_region" "current" {}

resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-${var.environment}-${var.service_name}-cluster"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_cloudwatch_log_group" "service_logs" {
  name              = "/ecs/${var.project_name}-${var.environment}-${var.service_name}"
  retention_in_days = 30
}

resource "aws_ecs_task_definition" "service_task" {
  family                   = "${var.project_name}-${var.environment}-${var.service_name}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.execution_role.arn
  
  # Conditional: Use external role if provided, else use the internal one created in iam.tf
task_role_arn = var.task_role_arn != null ? var.task_role_arn : aws_iam_role.task_role.arn

  container_definitions = jsonencode([{
    name      = var.service_name
    image     = var.ecr_image_uri
    essential = true

    # Conditional: Only map ports if a port is provided
    portMappings = var.container_port != null ? [{
      containerPort = var.container_port
      hostPort      = var.container_port
      protocol      = "tcp"
    }] : []

    environment = [
      for k, v in var.environment_variables : { name = k, value = v }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.service_logs.name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}

resource "aws_ecs_service" "main" {
  name            = "${var.project_name}-${var.environment}-${var.service_name}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.service_task.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs_sg.id]
    assign_public_ip = false
  }

  # Conditional: Only attach to ALB if a target group is provided
  dynamic "load_balancer" {
    for_each = var.target_group_arn != null ? [1] : []
    content {
      target_group_arn = var.target_group_arn
      container_name   = var.service_name
      container_port   = var.container_port
    }
  }
}

resource "aws_security_group" "ecs_sg" {
  name        = "${var.project_name}-${var.environment}-${var.service_name}-sg"
  vpc_id      = var.vpc_id
  description = "Security group for ECS service ${var.service_name}"

  ingress {
    from_port   = var.container_port != null ? var.container_port : 0
    to_port     = var.container_port != null ? var.container_port : 0
    protocol    = var.container_port != null ? "tcp" : "-1"
    cidr_blocks = ["0.0.0.0/0"] 
  }

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
}