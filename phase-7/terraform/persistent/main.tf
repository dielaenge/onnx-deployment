data "aws_caller_identity" "current" {}

# -------------------------------
# S3 BUCKET FOR PHASE 7 APP DATA
# -------------------------------
resource "aws_s3_bucket" "bape_app_data_phase7" {
  bucket = "bape-app-data-phase7-davidg"

  tags = {
    Name = "bape_app_data_phase7"
  }
}

resource "aws_s3_bucket_cors_configuration" "cors_config_phase7_app_data_bucket" {
  bucket = aws_s3_bucket.bape_app_data_phase7.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "GET", "HEAD"]
    allowed_origins = [
      # when running on AWS: "https://${aws_cloudfront_distribution.bape_phase7_frontend_s3_distribution.domain_name}",
      "http://127.0.0.1:8000",
      "http://localhost:8000",
      "*"
    ]
    expose_headers  = []
    max_age_seconds = 3000
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "bape_data_lifecycle" {
  bucket = aws_s3_bucket.bape_app_data_phase7.id

  rule {
    id     = "minimum_retention_policy"
    status = "Enabled"

    filter {
    }

    expiration {
      days = 1 # Minimum AWS S3 retention
    }
  }
}