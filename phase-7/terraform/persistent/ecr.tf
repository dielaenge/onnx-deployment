#---------------------------
# BAPE-INFERENCE-TF ECR REPO
#---------------------------
resource "aws_ecr_repository" "bape_ecr_phase7" {
  name                 = "bape-ecr-phase7"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "ECR-Repo_phase7"
  }
}

resource "aws_ecr_lifecycle_policy" "bape_ecr_phase7" {
  repository = aws_ecr_repository.bape_ecr_phase7.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after 1 day"
        selection = {
          tagStatus = "untagged"
          countType = "sinceImagePushed"
          countUnit = "days"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep 5 most recent images"
        selection = {
          tagStatus = "any"
          countType = "imageCountMoreThan"
          countNumber = 5
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}