resource "aws_cloudwatch_event_rule" "step_function_complete" {
  name        = "${var.project_name}-${var.environment}-pipeline-success-trigger"
  description = "Monitors Phase 2 Step Functions for completion to initialize the multi-agent execution state."

  event_pattern = jsonencode({
    source      = ["aws.states"]
    detail_type = ["Step Functions Execution Status Change"]
    detail = {
      status       = ["SUCCEEDED"]
      stateMachineArn = [var.step_function_arn]
    }
  })
}

resource "aws_iam_role" "eventbridge_ecs_role" {
  name = "${var.project_name}-${var.environment}-eventbridge-ecs-invoke-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "events.amazonaws.com" }
    }]
  })
}

resource "aws_iam_policy" "eventbridge_run_task" {
  name = "${var.project_name}-${var.environment}-eventbridge-runtask-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecs:RunTask"]
        Resource = [replace(var.ecs_task_definition_arn, "/:\\d+$/", ":*")]
      },
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Condition = {
          StringLike = {
            "iam:PassedToService" = "ecs-tasks.amazonaws.com"
          }
        }
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach_run_task" {
  role       = aws_iam_role.eventbridge_ecs_role.name
  policy_arn = aws_iam_policy.eventbridge_run_task.arn
}

resource "aws_cloudwatch_event_target" "ecs_target" {
  rule      = aws_cloudwatch_event_rule.step_function_complete.name
  target_id = "TriggerPhase3FargateAgent"
  arn       = var.ecs_cluster_arn
  role_arn  = aws_iam_role.eventbridge_ecs_role.arn

  ecs_target {
    task_count          = 1
    task_definition_arn = var.ecs_task_definition_arn
    launch_type         = "FARGATE"
    
    network_configuration {
      subnets          = var.private_subnet_ids
      security_groups  = [var.ecs_security_group_id]
      assign_public_ip = false
    }
  }

  # Maps the execution metadata down dynamically to the LangGraph application context
  input_transformer {
    input_paths = {
      execution_arn = "$.detail.executionArn"
      output_data   = "$.detail.output"
    }
    input_template = <<EOF
{
  "containerOverrides": [
    {
      "name": "dq-agent",
      "environment": [
        {"name": "PIPELINE_CORRELATION_ID", "value": <execution_arn>},
        {"name": "UPSTREAM_METADATA", "value": <output_data>}
      ]
    }
  ]
}
EOF
  }
}