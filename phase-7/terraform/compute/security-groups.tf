# ---------------
# SECURITY GROUPS
# ---------------
# Security Group for VPC Endpoints
resource "aws_security_group" "vpc_endpoint_sg" {
  name        = "vpc_endpoint_sg"
  description = "SG for VPC endpoints"
  vpc_id      = aws_vpc.bape-vpc.id

  tags = {
    Name = "vpc_endpoint_sg"
  }
}
# ingress rule: allow incoming HTTPS traffic from Fargate Container Security Group
resource "aws_vpc_security_group_ingress_rule" "vpc_endpoint_ingress" {
  security_group_id            = aws_security_group.vpc_endpoint_sg.id
  referenced_security_group_id = aws_security_group.ecs_fargate_containers_sg.id
  from_port                    = 443
  ip_protocol                  = "tcp"
  to_port                      = 443

  tags = {
    Name = "vpc_endpoint_sg_ingress"
  }
}
# NO EGRESS rule because *END*points are servers; they don't initiate connections

# ECS Fargate Container Security Group
resource "aws_security_group" "ecs_fargate_containers_sg" {
  name        = "ECS Fargate Containers SG"
  description = "Allow incoming traffic from BAPE ALB SG and outgoing, private traffic to Gateway endpoints (ECR, S3, CloudWatch.)"
  vpc_id      = aws_vpc.bape-vpc.id

  tags = {
    Name = "ecs_fargate_containers_sg"
  }
}
# ingress: allow incoming traffic from ALB Security Group on port 8080 (defined in dockerfile)
resource "aws_vpc_security_group_ingress_rule" "ecs_fargate_ingress" {
  security_group_id = aws_security_group.ecs_fargate_containers_sg.id

  referenced_security_group_id = aws_security_group.bape_alb_sg.id
  from_port                    = 8080
  ip_protocol                  = "tcp"
  to_port                      = 8080

  tags = {
    Name = "ecs_fargate_sg_ingress"
  }
}
# egress: allow outgoing traffic to the vpc endpoints
resource "aws_vpc_security_group_egress_rule" "ecs_fargate_egress" {
  security_group_id = aws_security_group.ecs_fargate_containers_sg.id

  referenced_security_group_id = aws_security_group.vpc_endpoint_sg.id
  from_port                    = 443
  ip_protocol                  = "tcp"
  to_port                      = 443

  tags = {
    Name = "ecs_fargate_sg_egress"
  }
}
# egress: allow traffic to S3 Gateway
# since S3 doesn't have an SG, I use a Prefix List
data "aws_ec2_managed_prefix_list" "s3" {
  name = "com.amazonaws.eu-central-1.s3"
}

resource "aws_vpc_security_group_egress_rule" "ecs_fargate_s3_egress" {
  security_group_id = aws_security_group.ecs_fargate_containers_sg.id

  prefix_list_id = data.aws_ec2_managed_prefix_list.s3.id
  from_port      = 443
  ip_protocol    = "tcp"
  to_port        = 443

  tags = {
    Name = "ecs_fargate_s3_sg_egress"
  }
}