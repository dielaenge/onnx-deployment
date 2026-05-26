# ---
# IAM 
# ---
# EXECUTION ROLE FOR ECS TASKS INCLUDING TRUST POLICY

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
    Name  = "bape_ecs_task_execution_role"
  }
}

# KEYS FOR EXECUTION ROLE (USING _ROLE_POLICY_ATTACHMENT FOR MANAGED POLICY)
resource "aws_iam_role_policy_attachment" "execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# TASK ROLE INCLUDING TRUST POLICY
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
    Name  = "bape-task-role"
  }
}

# KEYS FOR TASK ROLE (USING _ROLE_POLICY FOR CUSTOM POLICY)
resource "aws_iam_role_policy" "s3_access" {
  name = "bape-s3-access-policy"
  role = aws_iam_role.ecs_task_role.name
  policy = jsonencode(
    {
      Version = "2012-10-17"
      Statement = [{
        Action   = ["s3:GetObject", "s3:PutObject"]
        Effect   = "Allow"
        Resource = "${aws_s3_bucket.bape_app_data_phase6.arn}/*"
      }]
    }
  )
}
