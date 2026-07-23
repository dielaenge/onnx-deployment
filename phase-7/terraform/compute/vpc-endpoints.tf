# --------------
# VPC Endpoints
# --------------
# S3-Gateway Endpoint
resource "aws_vpc_endpoint" "s3-gateway" {
  vpc_id          = aws_vpc.bape-vpc.id
  service_name    = "com.amazonaws.eu-central-1.s3"
  route_table_ids = [aws_route_table.private-traffic.id]

  tags = {
    Name = "bape-vpc-s3-gw"
  }
}

# ECR API Interface Endpoint
resource "aws_vpc_endpoint" "ecr-api-interface" {
  vpc_id              = aws_vpc.bape-vpc.id
  service_name        = "com.amazonaws.eu-central-1.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.prv-sn-A.id, aws_subnet.prv-sn-B.id]
  private_dns_enabled = true
  security_group_ids  = [aws_security_group.vpc_endpoint_sg.id]

  tags = {
    Name = "bape-vpc-ecr-api-interface"
  }
}

# ECR Docker Interface Endpoint
resource "aws_vpc_endpoint" "ecr-dkr-interface" {
  vpc_id              = aws_vpc.bape-vpc.id
  service_name        = "com.amazonaws.eu-central-1.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.prv-sn-A.id, aws_subnet.prv-sn-B.id]
  private_dns_enabled = true
  security_group_ids  = [aws_security_group.vpc_endpoint_sg.id]

  tags = {
    Name = "bape-vpc-ecr-dkr-interface"
  }
}

# Cloudwatch Interface Endpoint
resource "aws_vpc_endpoint" "cloudwatch-logs-interface" {
  vpc_id              = aws_vpc.bape-vpc.id
  service_name        = "com.amazonaws.eu-central-1.logs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.prv-sn-A.id, aws_subnet.prv-sn-B.id]
  private_dns_enabled = true
  security_group_ids  = [aws_security_group.vpc_endpoint_sg.id]

  tags = {
    Name = "bape-vpc-cw-logs-interface"
  }
}

# SQS Interface Endpoint
resource "aws_vpc_endpoint" "sqs_interface" {
  vpc_id              = aws_vpc.bape-vpc.id
  service_name        = "com.amazonaws.eu-central-1.sqs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.prv-sn-A.id, aws_subnet.prv-sn-B.id]
  private_dns_enabled = true
  security_group_ids  = [aws_security_group.vpc_endpoint_sg.id]

  tags = {
    Name = "bape-vpc-sqs-endpoint"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "log_group_ecs_bape_inference_phase7" {
  name = "log-group-ecs-bape-inference-phase7"

  tags = {
    Name = "log_group_ecs_bape_inference"
  }
}