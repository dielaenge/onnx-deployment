# ALL RESOURCES AND DATA SOURCE BLOCKS

# ------------
# DATA SOURCES
# ------------
# AZ data source
data "aws_availability_zones" "available" {
  state = "available"
}
# Caller identity
data "aws_caller_identity" "current" {

}
# -------------------------------
# S3 BUCKET FOR PHASE 7 APP DATA
# -------------------------------
resource "aws_s3_bucket" "bape_app_data_phase7" {
  bucket = "bape-app-data-phase7-davidg"

  tags = {
    Name = "bape_app_data_phase7"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "bape_data_lifecycle" {
  bucket = aws_s3_bucket.bape_app_data_phase7.id

  rule {
    id     = "minimum_retention_policy"
    status = "Enabled"

    expiration {
      days = 1 # Minimum AWS S3 retention
    }
  }
}