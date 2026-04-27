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
    Phase = "phase-6-prod"
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