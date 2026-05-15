#--------------------------
# LOAD BALANCING
#--------------------------
# ALB Security Group 
resource "aws_security_group" "bape_alb_sg" {
  name        = "BAPE ALB SG"
  description = "Allow all incoming HTTPS traffic to BAPE ALB and forward as HTTP to private subnets."
  vpc_id      = aws_vpc.bape-vpc.id

  tags = {
    Name  = "bape_alb_sg"
    Phase = "phase-6-prod"
  }
}

# ingress: incoming HTTP/Port 80 (must be changed to HTTPS/443) traffic from all IPV4 addresses allowed
resource "aws_vpc_security_group_ingress_rule" "bape_alb_sg_ingress" {
  security_group_id = aws_security_group.bape_alb_sg.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 80
  ip_protocol       = "tcp"
  to_port           = 80
}

# egress: outgoing traffic to Fargate Container Security Group allowed / Port 8080 is the only exposed port by container
resource "aws_vpc_security_group_egress_rule" "bape_alb_sg_egress" {
  security_group_id = aws_security_group.bape_alb_sg.id

  referenced_security_group_id = aws_security_group.ecs_fargate_containers_sg.id
  from_port                    = 8080
  ip_protocol                  = "tcp"
  to_port                      = 8080
}

# APPLICATION LOAD BALANCER
resource "aws_lb" "bape_alb" {
  name               = "bape-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.bape_alb_sg.id]
  subnets            = [aws_subnet.pub-sn-A.id, aws_subnet.pub-sn-B.id]

  enable_deletion_protection = false

  idle_timeout = 3600

  tags = {
    Name  = "bape-alb"
    Phase = "phase-6-prod"
  }
}

# ALB Target Group: S3 Gateway and ECR API Interface endpoints
resource "aws_lb_target_group" "bape_alb_tg" {
  name        = "bape-alb-tg"
  target_type = "ip"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = aws_vpc.bape-vpc.id

  health_check {
    enabled             = true
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    healthy_threshold   = 3
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 5
    matcher             = "200"
  }

  tags = {
    Name  = "bape-alb-tg"
    Phase = "phase-6-prod"
  }
}

# ALB listener / listens for HTTP, forwards to target group
resource "aws_lb_listener" "bape_alb_listener" {
  load_balancer_arn = aws_lb.bape_alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.bape_alb_tg.arn
  }
}