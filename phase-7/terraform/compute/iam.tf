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

# MAIN TASK ROLE INCLUDING TRUST POLICY // GRANTING PERMISSIONS TO APPLICATION CODE
resource "aws_iam_role" "ecs_task_role" {
  name = "bape-main-task-role"
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

# WORKER TASK ROLE
resource "aws_iam_role" "ecs_worker_task_role" {
  name = "bape-worker-task-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
  tags = { 
    Name = "bape-worker-task-role" 
  }
}

# POLICY FOR MAIN TASK ROLE: S3 only for presigned URLs and upload –– had only 1 role previously for main and worker, disregarding rule of least privilege > split
resource "aws_iam_policy" "web_policy" {
  name = "bape_web_policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action   = ["s3:GetObject", "s3:PutObject"]
      Effect   = "Allow"
      Resource = "${data.aws_s3_bucket.bape_bucket.arn}/*"
    }]
  })
}

# POLICY FOR WORKER: S3 + SQS
resource "aws_iam_policy" "worker_policy" {
  name = "worker_policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
        Effect   = "Allow"
        Resource = data.aws_sqs_queue.bape_queue.arn
      },
      {
        Action   = ["s3:GetObject", "s3:PutObject"]
        Effect   = "Allow"
        Resource = "${data.aws_s3_bucket.bape_bucket.arn}/*"
      }
    ]
  })
}


resource "aws_iam_role_policy_attachment" "main_policy_attachment" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.web_policy.arn
}

resource "aws_iam_role_policy_attachment" "worker_policy_attachment" {
  role       = aws_iam_role.ecs_worker_task_role.name
  policy_arn = aws_iam_policy.worker_policy.arn
}
