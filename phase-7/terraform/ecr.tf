#---------------------------
# BAPE-INFERENCE-TF ECR REPO
#---------------------------
resource "aws_ecr_repository" "bape-phase7" {
  name                 = "bape-phase7"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "ECR-Repo_phase7"
  }
}
