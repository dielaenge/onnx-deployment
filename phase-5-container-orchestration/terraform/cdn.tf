resource "aws_s3_bucket" "bape_phase5_frontend" {
    bucket = "bape-phase5-frontend-davidg"

  tags = {
    Name = "bape_phase5_frontend_bucket"
  }
}

locals {
    s3_origin_id = "bape-phase5-frontend-s3-distribution"
}

# See https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html
data "aws_iam_policy_document" "origin_bucket_policy" {
  statement {
    sid    = "AllowCloudFrontServicePrincipalReadWrite"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    actions = [
      "s3:GetObject"    
      ]

    resources = [
      "${aws_s3_bucket.bape_phase5_frontend.arn}/*",
    ]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.bape_phase5_frontend_s3_distribution.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "bape_phase5_frontend_bucket_policy" {
  bucket = aws_s3_bucket.bape_phase5_frontend.bucket
  policy = data.aws_iam_policy_document.origin_bucket_policy.json
}

resource "aws_cloudfront_origin_access_control" "bape_phase5_oac" {
  name                              = "bape-phase5-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "bape_phase5_frontend_s3_distribution" {
  origin {
    domain_name              = aws_s3_bucket.bape_phase5_frontend.bucket_regional_domain_name
    origin_id = local.s3_origin_id
  }

  enabled             = true
  
  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = local.s3_origin_id

    viewer_protocol_policy = "redirect-to-https"
  }

  price_class = "PriceClass_100"

  restrictions {
    geo_restriction {
      restriction_type = "whitelist"
      locations        = ["US", "DE"]
    }
  }
  viewer_certificate {
    cloudfront_default_certificate = true
  }

  default_root_object = "index.html"
}