# ALL OUTPUT BLOCKS (APLPHABETICAL ORDER)
output "bape-inference-tf-repository_url" {
  description = "Repository URL for bape-inference-tf ECR repository"
  value       = aws_ecr_repository.bape-inference-tf.repository_url
}

output "cloudfront_phase5_url" {
  description = "Edge distribution URL serving the BAPE frontend."
  value       = aws_cloudfront_distribution.bape_phase5_frontend_s3_distribution.domain_name
}

# Output the Role ARN so we can copy it into our GitHub Actions YAML later
output "github_actions_role_arn" {
  description = "GitHub Actions IAM Role ARN. Copy into GitHub Actions YAML:"
  value       = aws_iam_role.github_actions_role.arn
}