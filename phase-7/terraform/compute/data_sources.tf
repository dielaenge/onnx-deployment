# Fetch app data bucket
data "aws_s3_bucket" "bape_bucket" {
    bucket = "bape-app-data-phase7-davidg"
}

# Fetch frontend bucket
data "aws_s3_bucket" "bape_frontend_bucket" {
    bucket = "bape-phase7-frontend-davidg"
}

# Fetch ECR repo
data "aws_ecr_repository" "bape_ecr" {
  name = "bape-ecr-phase7"
}

# Fetch SQS queue
data "aws_sqs_queue" "bape_queue" {
  name = "bape-cold-path-queue"
}

# Fetch available AZs
data "aws_availability_zones" "available" {
  state = "available"
}

# Caller identity
data "aws_caller_identity" "current" {

}