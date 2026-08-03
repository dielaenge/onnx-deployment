data "aws_s3_bucket" "bape_bucket" {
    bucket = "bape-app-data-phase7-davidg"
}

data "aws_s3_bucket" "bape_frontend_bucket" {
    bucket = "bape-phase7-frontend-davidg"
}

# Dynamically fetch your persistent ECR Repository [4]
data "aws_ecr_repository" "bape_ecr" {
  name = "bape-ecr-phase7"
}

# Dynamically fetch your persistent SQS Queue [4]
data "aws_sqs_queue" "bape_queue" {
  name = "bape-cold-path-queue"
}
data "aws_availability_zones" "available" {
  state = "available"
}

# Caller identity
data "aws_caller_identity" "current" {

}