# ---
# IAM 
# ---

# EXECUTION ROLE INCLUDING TRUST POLICY // GRANTING PERMISSIONS TO ECS AGENT
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "bape-task-execution-role"
  assume_role_policy = jsonencode(
    {
      Version = "2012-10-17"
      Statement = [{
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }]
    }
  )
  tags = {
    Name = "bape_ecs_task_execution_role"
  }
}

# TASK ROLE INCLUDING TRUST POLICY // GRANTING PERMISSIONS TO APPLICATION CODE
resource "aws_iam_role" "ecs_task_role" {
  name = "bape-task-role"
  assume_role_policy = jsonencode(
    {
      Version = "2012-10-17"
      Statement = [{
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }]
    }
  )
  tags = {
    Name = "bape-task-role"
  }
}

# ATTACH MANAGED POLICY TO TASK EXECUTION ROLE
resource "aws_iam_role_policy_attachment" "execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}


# CUSTOM POLICY FOR WORKER CONTAINER
resource "aws_iam_policy" "worker_policy" {
  name = "worker_policy"
  path = "/"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
        Effect   = "Allow"
        Resource = aws_sqs_queue.bape_cold_path_queue.arn
      },
      {
        Action   = ["s3:GetObject", "s3:PutObject"]
        Effect   = "Allow"
        Resource = "${aws_s3_bucket.bape_app_data_phase7.arn}/*"
      }
    ]
  })
}

# ATTACH CUSTOM POLICY TO TASK ROLE
resource "aws_iam_role_policy_attachment" "worker_policy_attachment" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.worker_policy.arn
}
