# ALL RESOURCES AND DATA SOURCE BLOCKS

# ------------
# DATA SOURCES
# ------------
# AZ data source
data "aws_availability_zones" "available" {
  state = "available"
}
# -------------------------------
# S3 BUCKET FOR PHASE 6 APP DATA
# -------------------------------
resource "aws_s3_bucket" "bape_app_data_phase6" {
  bucket = "bape-app-data-phase6-davidg"
}