resource "aws_s3_bucket" "bape_phase6_frontend" {
  bucket = "bape-phase6-frontend-davidg"

  tags = {
    Name = "bape_phase6_frontend_bucket"
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
      "${aws_s3_bucket.bape_phase6_frontend.arn}/*",
    ]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.bape_phase6_frontend_s3_distribution.arn]
    }
  }
}

data "aws_cloudfront_origin_request_policy" "all_viewer" {
  name = "Managed-AllViewer"
}

data "aws_cloudfront_cache_policy" "caching_disabled" {
  name = "Managed-CachingDisabled"
}

resource "aws_s3_bucket_policy" "bape_phase6_frontend_bucket_policy" {
  bucket = aws_s3_bucket.bape_phase6_frontend.bucket
  policy = data.aws_iam_policy_document.origin_bucket_policy.json
}

resource "aws_cloudfront_origin_access_control" "bape_phase6_oac" {
  name                              = "bape-phase6-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}


resource "aws_cloudfront_distribution" "bape_phase6_frontend_s3_distribution" {
  enabled = true

  origin {
    domain_name              = aws_s3_bucket.bape_phase6_frontend.bucket_regional_domain_name
    origin_id                = local.s3_origin_id
    origin_access_control_id = aws_cloudfront_origin_access_control.bape_phase6_oac.id
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
    path_pattern    = "/ws"
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods  = []
    cache_policy_id = data.aws_cloudfront_cache_policy.caching_disabled.id
    #AllViewer origin request policy
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.all_viewer.id
    target_origin_id         = aws_lb.bape_alb.id
    viewer_protocol_policy   = "redirect-to-https"
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