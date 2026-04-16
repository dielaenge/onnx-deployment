# ALL OUTPUT BLOCKS (APLPHABETICAL ORDER)
output "bape-inference-tf-repository_url" {
  description = "Repository URL for bape-inference-tf ECR repository"
  value       = aws_ecr_repository.bape-inference-tf.repository_url
}

output "cloudfront_phase5_url" {
  value =aws_cloudfront_distribution.bape_phase5_frontend_s3_distribution.domain_name
}