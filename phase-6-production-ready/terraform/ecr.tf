#---------------------------
# BAPE-INFERENCE-TF ECR REPO
#---------------------------
resource "aws_ecr_repository" "bape-phase6-inference" {
  name                 = "bape-phase6-inference"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}
