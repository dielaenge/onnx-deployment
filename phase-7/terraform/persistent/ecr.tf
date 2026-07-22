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
