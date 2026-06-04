# WHat is required for the cold path?
# - SQS queue
# - S3 bucket notification
# - SQS policy to allow S3 bucket to poll the SQS queue

resource "aws_sqs_queue" "bape_cold_path_queue" {
    name = "bape-cold-path-queue"
    visibility_timeout_seconds = 120
    
}

resource "aws_sqs_queue_policy" "bape_cold_path_queue_policy" {
    queue_url = aws_sqs_queue.bape_cold_path_queue.id
    
    policy = jsonencode({
    Version = "2012-10-17" # !! Important !!
    
    Statement = [{
      Sid    = "ALlow S3 bucket to get and send messages"
      Effect = "Allow"
    
      Principal = {
        Service = "s3.amazonaws.com"
      }
    
      Action   = ["SQS:SendMessage"]

      Resource = aws_sqs_queue.bape_cold_path_queue.arn
      
      Condition = {
        ArnLike = {
          "aws:SourceArn" = aws_s3_bucket.bape_app_data_phase7_davidg.arn
        }
      }
    }]
  })
}

resource "aws_s3_bucket_notification" "bape_s3_notification" {
    bucket = "bape-app-data-phase7-davidg"

    queue {
        events = ["s3:ObjectCreated:*"]
        filter_prefix = "uploads/"
        queue_arn = aws_sqs_queue.bape_cold_path_queue.arn
    }
}