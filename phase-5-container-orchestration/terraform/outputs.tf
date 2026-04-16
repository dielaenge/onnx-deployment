# ALL OUTPUT BLOCKS (APLPHABETICAL ORDER)
output "bape-inference-tf-repository_url" {
  description = "Repository URL for bape-inference-tf ECR repository"
  value       = aws_ecr_repository.bape-inference-tf.repository_url
}