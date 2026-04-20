# ALL OUTPUT BLOCKS (APLPHABETICAL ORDER)
output "bape-inference-tf-repository_url" {
  description = "Repository URL for bape-inference-tf ECR repository"
  value       = aws_ecr_repository.bape-inference-tf.repository_url
}

output "cloudfront_phase5_url" {
  description = "Edge distribution URL serving the BAPE frontend."
  value       = aws_cloudfront_distribution.bape_phase5_frontend_s3_distribution.domain_name
}

output "bape_alb_dns_name" {
  description = "DNS name of phase 5 ALB."
  value       = aws_lb.bape_alb.dns_name
}