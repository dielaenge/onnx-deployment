# ---
# ECS
# ---

# TASK DEFINITION
resource "aws_ecs_task_definition" "task_definition_bape" {
  family                   = "task_definition_bape"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024
  container_definitions = jsonencode([
    {
      name      = "bape-container"
      image     = "${aws_ecr_repository.bape_ecr_phase7.repository_url}:phase7"
      essential = true
      portMappings = [
        {
          containerPort = 8080
          hostPort      = 8080
        }
      ]
      environment = [
        {
          "name" : "NUMBA_CACHE_DIR",
          "value" : "/tmp"
        },
        {
          "name"  = "JOBLIB_TEMP_FOLDER",
          "value" = "/tmp"
        },
        {
          "name"  = "APP_DATA_BUCKET_NAME",
          "value" = aws_s3_bucket.bape_app_data_phase7.id
        },
        {
          "name"  = "AWS_REGION",
          "value" = data.aws_region.current.name
        },
        {
          "name"  = "UVICORN_HOST",
          "value" = "0.0.0.0"

        },
        {
          "name"  = "UVICORN_PORT",
          "value" = "8080"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs",
        options = {
          "awslogs-group"  = aws_cloudwatch_log_group.log_group_ecs_bape_inference_phase7.name
          "awslogs-region" = "eu-central-1"
          "awslogs-stream-prefix" : "bape-ecs-phase7_"
        }
      }
    }
  ])
}

# ECS Cluster
resource "aws_ecs_cluster" "bape_cluster" {
  name = "bape_cluster"
  setting {
    name  = "containerInsights"
    value = "enhanced"
  }

  tags = {
    Name = "bape_cluster"
  }
}

# ECS Service
resource "aws_ecs_service" "bape_service" {
  name            = "bape_ecs_service"
  cluster         = aws_ecs_cluster.bape_cluster.id
  task_definition = aws_ecs_task_definition.task_definition_bape.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    assign_public_ip = false # default
    subnets          = [aws_subnet.prv-sn-A.id, aws_subnet.prv-sn-B.id]
    security_groups  = [aws_security_group.ecs_fargate_containers_sg.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.bape_alb_tg.arn
    container_name   = "bape-container"
    container_port   = 8080
  }

  tags = {
    Name = "bape_ecs_service"
  }

}