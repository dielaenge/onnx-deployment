# ALL RESOURCES AND DATA SOURCE BLOCKS

# ------------
# DATA SOURCES
# ------------
# AZ data source
data "aws_availability_zones" "available" {
  state = "available"
}
# -------------------------------
# S3 BUCKET FOR PHASE 5 APP DATA
# -------------------------------
resource "aws_s3_bucket" "bape_app_data_phase5" {
  bucket = "bape-app-data-phase5-davidg"
}
# ---
# VPC
# ---
# VPC
resource "aws_vpc" "bape-vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name  = "bape-vpc"
    Phase = "phase-5-ecs"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.bape-vpc.id

  tags = {
    Name  = "bape-vpc-igw"
    Phase = "phase-5-ecs"
  }
}

# Subnets
resource "aws_subnet" "pub-sn-A" {
  vpc_id            = aws_vpc.bape-vpc.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]
  tags = {
    Name  = "bape-vpc-pub-sn-A"
    Phase = "phase-5-ecs"
  }
}

resource "aws_subnet" "pub-sn-B" {
  vpc_id            = aws_vpc.bape-vpc.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]
  tags = {
    Name  = "bape-vpc-pub-sn-B"
    Phase = "phase-5-ecs"
  }
}

resource "aws_subnet" "prv-sn-A" {
  vpc_id            = aws_vpc.bape-vpc.id
  cidr_block        = "10.0.3.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]
  tags = {
    Name  = "bape-vpc-prv-sn-A"
    Phase = "phase-5-ecs"
  }
}

resource "aws_subnet" "prv-sn-B" {
  vpc_id            = aws_vpc.bape-vpc.id
  cidr_block        = "10.0.4.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]
  tags = {
    Name  = "bape-vpc-prv-sn-B"
    Phase = "phase-5-ecs"
  }
}

# -------
# ROUTING
# -------
# Route Table for Public Subnets: All Traffic --> IGW
resource "aws_route_table" "all-traffic-to-igw" {
  vpc_id = aws_vpc.bape-vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name  = "bape-vpc-route-table"
    Phase = "phase-5-ecs"
  }
}

# associate `all-taffic-to-igw` with public subnets
resource "aws_route_table_association" "pub-sn-a-assoc" {
  subnet_id      = aws_subnet.pub-sn-A.id
  route_table_id = aws_route_table.all-traffic-to-igw.id
}

resource "aws_route_table_association" "pub-sn-b-assoc" {
  subnet_id      = aws_subnet.pub-sn-B.id
  route_table_id = aws_route_table.all-traffic-to-igw.id
}
# Route Table for Private Subnets: ??
resource "aws_route_table" "private-traffic" {
  vpc_id = aws_vpc.bape-vpc.id
}
# associate `private-traffic` with private subnets
resource "aws_route_table_association" "prv-sn-a-assoc" {
  subnet_id      = aws_subnet.prv-sn-A.id
  route_table_id = aws_route_table.private-traffic.id
}

resource "aws_route_table_association" "prv-sn-b-assoc" {
  subnet_id      = aws_subnet.prv-sn-B.id
  route_table_id = aws_route_table.private-traffic.id
}

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
    Phase = "phase-5-ecs"
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

  tags = {
    Name  = "bape-alb"
    Phase = "phase-5-ecs"
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
    Phase = "phase-5-ecs"
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

# --------------
# VPC Endpoints
# --------------
# S3-Gateway Endpoint
resource "aws_vpc_endpoint" "s3-gateway" {
  vpc_id          = aws_vpc.bape-vpc.id
  service_name    = "com.amazonaws.eu-central-1.s3"
  route_table_ids = [aws_route_table.private-traffic.id]

  tags = {
    Name  = "bape-vpc-s3-gw"
    Phase = "phase-5-ecs"
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
    Name  = "bape-vpc-ecr-api-interface"
    Phase = "phase-5-ecs"
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
    Name  = "bape-vpc-ecr-dkr-interface"
    Phase = "phase-5-ecs"
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
    Name  = "bape-vpc-cw-logs-interface"
    Phase = "phase-5-ecs"
  }
}
# CloudWatch Log Group

resource "aws_cloudwatch_log_group" "log_group_ecs_bape_inference" {
  name = "log-group-ecs-bape-inference"

  tags = {
    Name  = "log_group_ecs_bape_inference"
    Phase = "phase-5-ecs"
  }
}

# Security Group for VPC Endpoints
resource "aws_security_group" "vpc_endpoint_sg" {
  name        = "vpc_endpoint_sg"
  description = "SG for VPC endpoints"
  vpc_id      = aws_vpc.bape-vpc.id

  tags = {
    Name  = "vpc_endpoint_sg"
    Phase = "phase-5-ecs"
  }
}
# ingress rule: allow incoming HTTPS traffic from Fargate Container Security Group
resource "aws_vpc_security_group_ingress_rule" "vpc_endpoint_ingress" {
  security_group_id            = aws_security_group.vpc_endpoint_sg.id
  referenced_security_group_id = aws_security_group.ecs_fargate_containers_sg.id
  from_port                    = 443
  ip_protocol                  = "tcp"
  to_port                      = 443
}
# NO EGRESS rule because *END*points are servers; they don't initiate connections
#---------------------------
# BAPE-INFERENCE-TF ECR REPO
#---------------------------
resource "aws_ecr_repository" "bape-inference-tf" {
  name                 = "bape-inference-tf"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}
#---------------------------
# ECS FARGATE SECURITY GROUP
#---------------------------
# Fargate Container Security Group
resource "aws_security_group" "ecs_fargate_containers_sg" {
  name        = "ECS Fargate Conatiners SG"
  description = "Allow incoming traffic from BAPE ALB SG and outgoing, private traffic to Gateway endpoints (ECR, S3, CloudWatch.)"
  vpc_id      = aws_vpc.bape-vpc.id

  tags = {
    Name  = "ecs_fargate_containers_sg"
    Phase = "phase-5-ecs"
  }
}
# ingress: allow incoming traffic from ALB Security Group on port 8080 (defined in dockerfile)
resource "aws_vpc_security_group_ingress_rule" "ecs_fargate_ingress" {
  security_group_id = aws_security_group.ecs_fargate_containers_sg.id

  referenced_security_group_id = aws_security_group.bape_alb_sg.id
  from_port                    = 8080
  ip_protocol                  = "tcp"
  to_port                      = 8080
}
# egress: allow outgoing traffic to the vpc endpoints
resource "aws_vpc_security_group_egress_rule" "ecs_fargate_egress" {
  security_group_id = aws_security_group.ecs_fargate_containers_sg.id

  referenced_security_group_id = aws_security_group.vpc_endpoint_sg.id
  from_port                    = 443
  ip_protocol                  = "tcp"
  to_port                      = 443
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
}



# IAM FOR ECS

# EXECUTION ROLE FOR ECS TASKS INCLUDING TRUST POLICY

resource "aws_iam_role" "ecs_task_execution_role" {
  name = "bape-task-execution-role"
  assume_role_policy = jsonencode(
    {
      Version = "2012-10-17"
      Statement = [{
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }]
    }
  )
  tags = {
    Name  = "bape_ecs_task_execution_role"
    Phase = "phase-5-ecs"
  }
}

# KEYS FOR EXECUTION ROLE (USING _ROLE_POLICY_ATTACHMENT FOR MANAGED POLICY)
resource "aws_iam_role_policy_attachment" "execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# TASK ROLE INCLUDING TRUST POLICY
resource "aws_iam_role" "ecs_task_role" {
  name = "bape-task-role"
  assume_role_policy = jsonencode(
    {
      Version = "2012-10-17"
      Statement = [{
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }]
    }
  )
}

# KEYS FOR TASK ROLE (USING _ROLE_POLICY FOR CUSTOM POLICY)
resource "aws_iam_role_policy" "s3_access" {
  name = "bape-s3-access-policy"
  role = aws_iam_role.ecs_task_role.name
  policy = jsonencode(
    {
      Version = "2012-10-17"
      Statement = [{
        Action   = ["s3:GetObject", "s3:PutObject"]
        Effect   = "Allow"
        Resource = "${aws_s3_bucket.bape_app_data_phase5.arn}/*"
      }]
    }
  )
}

#TASK DEFINITION


resource "aws_ecs_task_definition" "task_definition_bape" {
  family                   = "task_definition_bape"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  container_definitions = jsonencode([
    {
      name      = "bape-container"
      image     = "${aws_ecr_repository.bape-inference-tf.repository_url}:v2.0.0-tf-standardized"
      essential = true
      portMappings = [
        {
          containerPort = 8080
          hostPort      = 8080
        }
      ]
      environment = [
        {
          "name" : "NUMBA_CACHE_DIR",
          "value" : "/tmp"
        },
        {
          "name"  = "JOBLIB_TEMP_FOLDER",
          "value" = "/tmp"
        },
        {
          name  = "APP_BUCKET_NAME"
          value = aws_s3_bucket.bape_app_data_phase5.id
        }
      ]
      logConfiguration = {
        logDriver = "awslogs",
        options = {
          "awslogs-group"  = aws_cloudwatch_log_group.log_group_ecs_bape_inference.name
          "awslogs-region" = "eu-central-1"
          "awslogs-stream-prefix" : "bape-ecs_"
        }
      }
    }
  ])
}

# ECS Cluster
resource "aws_ecs_cluster" "bape_cluster" {
  name = "bape_cluster"
}

# ECS Service
resource "aws_ecs_service" "bape_service" {
  name            = "bape_ecs_service"
  cluster         = aws_ecs_cluster.bape_cluster.id
  task_definition = aws_ecs_task_definition.task_definition_bape.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    assign_public_ip = false # default
    subnets          = [aws_subnet.prv-sn-A.id, aws_subnet.prv-sn-B.id]
    security_groups  = [aws_security_group.ecs_fargate_containers_sg.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.bape_alb_tg.arn
    container_name   = "bape-container"
    container_port   = 8080
  }
}