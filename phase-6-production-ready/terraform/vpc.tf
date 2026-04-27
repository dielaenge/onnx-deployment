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
    Phase = "phase-6-prod"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.bape-vpc.id

  tags = {
    Name  = "bape-vpc-igw"
    Phase = "phase-6-prod"
  }
}

# Subnets
resource "aws_subnet" "pub-sn-A" {
  vpc_id            = aws_vpc.bape-vpc.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]
  tags = {
    Name  = "bape-vpc-pub-sn-A"
    Phase = "phase-6-prod"
  }
}

resource "aws_subnet" "pub-sn-B" {
  vpc_id            = aws_vpc.bape-vpc.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]
  tags = {
    Name  = "bape-vpc-pub-sn-B"
    Phase = "phase-6-prod"
  }
}

resource "aws_subnet" "prv-sn-A" {
  vpc_id            = aws_vpc.bape-vpc.id
  cidr_block        = "10.0.3.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]
  tags = {
    Name  = "bape-vpc-prv-sn-A"
    Phase = "phase-6-prod"
  }
}

resource "aws_subnet" "prv-sn-B" {
  vpc_id            = aws_vpc.bape-vpc.id
  cidr_block        = "10.0.4.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]
  tags = {
    Name  = "bape-vpc-prv-sn-B"
    Phase = "phase-6-prod"
  }
}
