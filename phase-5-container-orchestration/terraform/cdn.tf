resource "aws_s3_bucket" "bape_phase5_frontend" {
  bucket = "bape-phase5-frontend-davidg"

  tags = {
    Name = "bape_phase5_frontend_bucket"
  }
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

locals {
  s3_origin_id = "bape-phase5-frontend-s3-distribution"
}

resource "aws_cloudfront_distribution" "bape_phase5_frontend_s3_distribution" {
  enabled = true

  origin {
    domain_name              = aws_s3_bucket.bape_phase5_frontend.bucket_regional_domain_name
    origin_id                = local.s3_origin_id
    origin_access_control_id = aws_cloudfront_origin_access_control.bape_phase5_oac.id
  }

  origin {
    domain_name = aws_lb.bape_alb.dns_name
    origin_id   = aws_lb.bape_alb.id
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = local.s3_origin_id

    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  ordered_cache_behavior {
    path_pattern    = "/acou-vec/*"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods  = ["GET", "HEAD"]
    #CachingDisabled Policy
    cache_policy_id        = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
    target_origin_id       = aws_lb.bape_alb.id
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