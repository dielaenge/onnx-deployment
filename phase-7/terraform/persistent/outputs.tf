output "bape_bucket" {
    description = "Name of BAPE app data bucket."
    value = aws_s3_bucket.bape_app_data_phase7.id
}

output "sqs_queue_url" {
  description = "SQS queue URL for cold path."
  value = aws_sqs_queue.bape_cold_path_queue.id
}