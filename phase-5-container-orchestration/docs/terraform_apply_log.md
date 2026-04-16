The returned statement after drafting, validating and applying the phase 5 infrastructure

```zsh
onnx-acoustic/phase-5-container-orchestration/terraform on  feat/container-orchestration [$✘»!+?] via 🐍 v3.11.15 (python-3.11) via 💠 default on ☁️  dev (eu-central-1) took 3s 
❯ tf apply
data.aws_ec2_managed_prefix_list.s3: Reading...
data.aws_availability_zones.available: Reading...
aws_ecr_repository.bape-inference-tf: Refreshing state... [id=bape-inference-tf]
data.aws_availability_zones.available: Read complete after 0s [id=eu-central-1]
data.aws_ec2_managed_prefix_list.s3: Read complete after 1s [id=pl-6ea54007]

Terraform used the selected providers to generate the following execution plan. Resource actions are indicated with the following symbols:
  + create

Terraform will perform the following actions:

  # aws_cloudwatch_log_group.log_group_ecs_bape_inference will be created
  + resource "aws_cloudwatch_log_group" "log_group_ecs_bape_inference" {
      + arn               = (known after apply)
      + id                = (known after apply)
      + log_group_class   = (known after apply)
      + name              = "log-group-ecs-bape-inference"
      + name_prefix       = (known after apply)
      + retention_in_days = 0
      + skip_destroy      = false
      + tags              = {
          + "Name"  = "log_group_ecs_bape_inference"
          + "Phase" = "phase-5-ecs"
        }
      + tags_all          = {
          + "Name"  = "log_group_ecs_bape_inference"
          + "Phase" = "phase-5-ecs"
        }
    }

  # aws_ecs_cluster.bape_cluster will be created
  + resource "aws_ecs_cluster" "bape_cluster" {
      + arn      = (known after apply)
      + id       = (known after apply)
      + name     = "bape_cluster"
      + tags_all = (known after apply)

      + setting (known after apply)
    }

  # aws_ecs_service.bape_service will be created
  + resource "aws_ecs_service" "bape_service" {
      + availability_zone_rebalancing      = "DISABLED"
      + cluster                            = (known after apply)
      + deployment_maximum_percent         = 200
      + deployment_minimum_healthy_percent = 100
      + desired_count                      = 1
      + enable_ecs_managed_tags            = false
      + enable_execute_command             = false
      + iam_role                           = (known after apply)
      + id                                 = (known after apply)
      + launch_type                        = "FARGATE"
      + name                               = "bape_ecs_service"
      + platform_version                   = (known after apply)
      + scheduling_strategy                = "REPLICA"
      + tags_all                           = (known after apply)
      + task_definition                    = (known after apply)
      + triggers                           = (known after apply)
      + wait_for_steady_state              = false

      + load_balancer {
          + container_name   = "bape-container"
          + container_port   = 8080
          + target_group_arn = (known after apply)
            # (1 unchanged attribute hidden)
        }

      + network_configuration {
          + assign_public_ip = false
          + security_groups  = (known after apply)
          + subnets          = (known after apply)
        }
    }

  # aws_ecs_task_definition.task_definition_bape will be created
  + resource "aws_ecs_task_definition" "task_definition_bape" {
      + arn                      = (known after apply)
      + arn_without_revision     = (known after apply)
      + container_definitions    = jsonencode(
            [
              + {
                  + environment      = [
                      + {
                          + name  = "JOBLIB_TEMP_FOLDER"
                          + value = "/tmp"
                        },
                      + {
                          + name  = "NUMBA_CACHE_DIR"
                          + value = "/tmp"
                        },
                    ]
                  + essential        = true
                  + image            = "609662023678.dkr.ecr.eu-central-1.amazonaws.com/bape-inference-tf:inference-fix-2026-04-14"
                  + logConfiguration = {
                      + logDriver = "awslogs"
                      + options   = {
                          + awslogs-group         = "log-group-ecs-bape-inference"
                          + awslogs-region        = "eu-central-1"
                          + awslogs-stream-prefix = "bape-ecs_"
                        }
                    }
                  + name             = "bape-container"
                  + portMappings     = [
                      + {
                          + containerPort = 8080
                          + hostPort      = 8080
                        },
                    ]
                },
            ]
        )
      + cpu                      = "256"
      + enable_fault_injection   = (known after apply)
      + execution_role_arn       = (known after apply)
      + family                   = "task_definition_bape"
      + id                       = (known after apply)
      + memory                   = "512"
      + network_mode             = "awsvpc"
      + requires_compatibilities = [
          + "FARGATE",
        ]
      + revision                 = (known after apply)
      + skip_destroy             = false
      + tags_all                 = (known after apply)
      + task_role_arn            = (known after apply)
      + track_latest             = false
    }

  # aws_iam_role.ecs_task_execution_role will be created
  + resource "aws_iam_role" "ecs_task_execution_role" {
      + arn                   = (known after apply)
      + assume_role_policy    = jsonencode(
            {
              + Statement = [
                  + {
                      + Action    = "sts:AssumeRole"
                      + Effect    = "Allow"
                      + Principal = {
                          + Service = "ecs-tasks.amazonaws.com"
                        }
                      + Sid       = ""
                    },
                ]
              + Version   = "2012-10-17"
            }
        )
      + create_date           = (known after apply)
      + force_detach_policies = false
      + id                    = (known after apply)
      + managed_policy_arns   = (known after apply)
      + max_session_duration  = 3600
      + name                  = "bape-task-execution-role"
      + name_prefix           = (known after apply)
      + path                  = "/"
      + tags                  = {
          + "Name"  = "bape_ecs_task_execution_role"
          + "Phase" = "phase-5-ecs"
        }
      + tags_all              = {
          + "Name"  = "bape_ecs_task_execution_role"
          + "Phase" = "phase-5-ecs"
        }
      + unique_id             = (known after apply)

      + inline_policy (known after apply)
    }

  # aws_iam_role.ecs_task_role will be created
  + resource "aws_iam_role" "ecs_task_role" {
      + arn                   = (known after apply)
      + assume_role_policy    = jsonencode(
            {
              + Statement = [
                  + {
                      + Action    = "sts:AssumeRole"
                      + Effect    = "Allow"
                      + Principal = {
                          + Service = "ecs-tasks.amazonaws.com"
                        }
                      + Sid       = ""
                    },
                ]
              + Version   = "2012-10-17"
            }
        )
      + create_date           = (known after apply)
      + force_detach_policies = false
      + id                    = (known after apply)
      + managed_policy_arns   = (known after apply)
      + max_session_duration  = 3600
      + name                  = "bape-task-role"
      + name_prefix           = (known after apply)
      + path                  = "/"
      + tags_all              = (known after apply)
      + unique_id             = (known after apply)

      + inline_policy (known after apply)
    }

  # aws_iam_role_policy.s3_access will be created
  + resource "aws_iam_role_policy" "s3_access" {
      + id          = (known after apply)
      + name        = "bape-s3-access-policy"
      + name_prefix = (known after apply)
      + policy      = jsonencode(
            {
              + Statement = [
                  + {
                      + Action   = [
                          + "s3:GetObject",
                          + "s3:PutObject",
                        ]
                      + Effect   = "Allow"
                      + Resource = "arn:aws:s3:::bape-app-data-phase5-davidg"
                    },
                ]
              + Version   = "2012-10-17"
            }
        )
      + role        = "bape-task-role"
    }

  # aws_iam_role_policy_attachment.execution_role_policy will be created
  + resource "aws_iam_role_policy_attachment" "execution_role_policy" {
      + id         = (known after apply)
      + policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
      + role       = "bape-task-execution-role"
    }

  # aws_internet_gateway.igw will be created
  + resource "aws_internet_gateway" "igw" {
      + arn      = (known after apply)
      + id       = (known after apply)
      + owner_id = (known after apply)
      + tags     = {
          + "Name"  = "bape-vpc-igw"
          + "Phase" = "phase-5-ecs"
        }
      + tags_all = {
          + "Name"  = "bape-vpc-igw"
          + "Phase" = "phase-5-ecs"
        }
      + vpc_id   = (known after apply)
    }

  # aws_lb.bape_alb will be created
  + resource "aws_lb" "bape_alb" {
      + arn                                                          = (known after apply)
      + arn_suffix                                                   = (known after apply)
      + client_keep_alive                                            = 3600
      + desync_mitigation_mode                                       = "defensive"
      + dns_name                                                     = (known after apply)
      + drop_invalid_header_fields                                   = false
      + enable_deletion_protection                                   = true
      + enable_http2                                                 = true
      + enable_tls_version_and_cipher_suite_headers                  = false
      + enable_waf_fail_open                                         = false
      + enable_xff_client_port                                       = false
      + enable_zonal_shift                                           = false
      + enforce_security_group_inbound_rules_on_private_link_traffic = (known after apply)
      + id                                                           = (known after apply)
      + idle_timeout                                                 = 60
      + internal                                                     = false
      + ip_address_type                                              = (known after apply)
      + load_balancer_type                                           = "application"
      + name                                                         = "bape-alb"
      + name_prefix                                                  = (known after apply)
      + preserve_host_header                                         = false
      + security_groups                                              = (known after apply)
      + subnets                                                      = (known after apply)
      + tags                                                         = {
          + "Name"  = "bape-alb"
          + "Phase" = "phase-5-ecs"
        }
      + tags_all                                                     = {
          + "Name"  = "bape-alb"
          + "Phase" = "phase-5-ecs"
        }
      + vpc_id                                                       = (known after apply)
      + xff_header_processing_mode                                   = "append"
      + zone_id                                                      = (known after apply)

      + subnet_mapping (known after apply)
    }

  # aws_lb_listener.bape_alb_listener will be created
  + resource "aws_lb_listener" "bape_alb_listener" {
      + arn                                                                   = (known after apply)
      + id                                                                    = (known after apply)
      + load_balancer_arn                                                     = (known after apply)
      + port                                                                  = 80
      + protocol                                                              = "HTTP"
      + routing_http_request_x_amzn_mtls_clientcert_header_name               = (known after apply)
      + routing_http_request_x_amzn_mtls_clientcert_issuer_header_name        = (known after apply)
      + routing_http_request_x_amzn_mtls_clientcert_leaf_header_name          = (known after apply)
      + routing_http_request_x_amzn_mtls_clientcert_serial_number_header_name = (known after apply)
      + routing_http_request_x_amzn_mtls_clientcert_subject_header_name       = (known after apply)
      + routing_http_request_x_amzn_mtls_clientcert_validity_header_name      = (known after apply)
      + routing_http_request_x_amzn_tls_cipher_suite_header_name              = (known after apply)
      + routing_http_request_x_amzn_tls_version_header_name                   = (known after apply)
      + routing_http_response_access_control_allow_credentials_header_value   = (known after apply)
      + routing_http_response_access_control_allow_headers_header_value       = (known after apply)
      + routing_http_response_access_control_allow_methods_header_value       = (known after apply)
      + routing_http_response_access_control_allow_origin_header_value        = (known after apply)
      + routing_http_response_access_control_expose_headers_header_value      = (known after apply)
      + routing_http_response_access_control_max_age_header_value             = (known after apply)
      + routing_http_response_content_security_policy_header_value            = (known after apply)
      + routing_http_response_server_enabled                                  = (known after apply)
      + routing_http_response_strict_transport_security_header_value          = (known after apply)
      + routing_http_response_x_content_type_options_header_value             = (known after apply)
      + routing_http_response_x_frame_options_header_value                    = (known after apply)
      + ssl_policy                                                            = (known after apply)
      + tags_all                                                              = (known after apply)
      + tcp_idle_timeout_seconds                                              = (known after apply)

      + default_action {
          + order            = (known after apply)
          + target_group_arn = (known after apply)
          + type             = "forward"
        }

      + mutual_authentication (known after apply)
    }

  # aws_lb_target_group.bape_alb_tg will be created
  + resource "aws_lb_target_group" "bape_alb_tg" {
      + arn                                = (known after apply)
      + arn_suffix                         = (known after apply)
      + connection_termination             = (known after apply)
      + deregistration_delay               = "300"
      + id                                 = (known after apply)
      + ip_address_type                    = (known after apply)
      + lambda_multi_value_headers_enabled = false
      + load_balancer_arns                 = (known after apply)
      + load_balancing_algorithm_type      = (known after apply)
      + load_balancing_anomaly_mitigation  = (known after apply)
      + load_balancing_cross_zone_enabled  = (known after apply)
      + name                               = "bape-alb-tg"
      + name_prefix                        = (known after apply)
      + port                               = 8080
      + preserve_client_ip                 = (known after apply)
      + protocol                           = "HTTP"
      + protocol_version                   = (known after apply)
      + proxy_protocol_v2                  = false
      + slow_start                         = 0
      + tags                               = {
          + "Name"  = "bape-alb-tg"
          + "Phase" = "phase-5-ecs"
        }
      + tags_all                           = {
          + "Name"  = "bape-alb-tg"
          + "Phase" = "phase-5-ecs"
        }
      + target_type                        = "ip"
      + vpc_id                             = (known after apply)

      + health_check {
          + enabled             = true
          + healthy_threshold   = 3
          + interval            = 30
          + matcher             = "200"
          + path                = "/health"
          + port                = "traffic-port"
          + protocol            = "HTTP"
          + timeout             = 5
          + unhealthy_threshold = 3
        }

      + stickiness (known after apply)

      + target_failover (known after apply)

      + target_group_health (known after apply)

      + target_health_state (known after apply)
    }

  # aws_route_table.all-traffic-to-igw will be created
  + resource "aws_route_table" "all-traffic-to-igw" {
      + arn              = (known after apply)
      + id               = (known after apply)
      + owner_id         = (known after apply)
      + propagating_vgws = (known after apply)
      + route            = [
          + {
              + cidr_block                 = "0.0.0.0/0"
              + gateway_id                 = (known after apply)
                # (11 unchanged attributes hidden)
            },
        ]
      + tags             = {
          + "Name"  = "bape-vpc-route-table"
          + "Phase" = "phase-5-ecs"
        }
      + tags_all         = {
          + "Name"  = "bape-vpc-route-table"
          + "Phase" = "phase-5-ecs"
        }
      + vpc_id           = (known after apply)
    }

  # aws_route_table.private-traffic will be created
  + resource "aws_route_table" "private-traffic" {
      + arn              = (known after apply)
      + id               = (known after apply)
      + owner_id         = (known after apply)
      + propagating_vgws = (known after apply)
      + route            = (known after apply)
      + tags_all         = (known after apply)
      + vpc_id           = (known after apply)
    }

  # aws_route_table_association.prv-sn-a-assoc will be created
  + resource "aws_route_table_association" "prv-sn-a-assoc" {
      + id             = (known after apply)
      + route_table_id = (known after apply)
      + subnet_id      = (known after apply)
    }

  # aws_route_table_association.prv-sn-b-assoc will be created
  + resource "aws_route_table_association" "prv-sn-b-assoc" {
      + id             = (known after apply)
      + route_table_id = (known after apply)
      + subnet_id      = (known after apply)
    }

  # aws_route_table_association.pub-sn-a-assoc will be created
  + resource "aws_route_table_association" "pub-sn-a-assoc" {
      + id             = (known after apply)
      + route_table_id = (known after apply)
      + subnet_id      = (known after apply)
    }

  # aws_route_table_association.pub-sn-b-assoc will be created
  + resource "aws_route_table_association" "pub-sn-b-assoc" {
      + id             = (known after apply)
      + route_table_id = (known after apply)
      + subnet_id      = (known after apply)
    }

  # aws_s3_bucket.bape_app_data_phase5 will be created
  + resource "aws_s3_bucket" "bape_app_data_phase5" {
      + acceleration_status         = (known after apply)
      + acl                         = (known after apply)
      + arn                         = (known after apply)
      + bucket                      = "bape-app-data-phase5-davidg"
      + bucket_domain_name          = (known after apply)
      + bucket_prefix               = (known after apply)
      + bucket_regional_domain_name = (known after apply)
      + force_destroy               = false
      + hosted_zone_id              = (known after apply)
      + id                          = (known after apply)
      + object_lock_enabled         = (known after apply)
      + policy                      = (known after apply)
      + region                      = (known after apply)
      + request_payer               = (known after apply)
      + tags_all                    = (known after apply)
      + website_domain              = (known after apply)
      + website_endpoint            = (known after apply)

      + cors_rule (known after apply)

      + grant (known after apply)

      + lifecycle_rule (known after apply)

      + logging (known after apply)

      + object_lock_configuration (known after apply)

      + replication_configuration (known after apply)

      + server_side_encryption_configuration (known after apply)

      + versioning (known after apply)

      + website (known after apply)
    }

  # aws_security_group.bape_alb_sg will be created
  + resource "aws_security_group" "bape_alb_sg" {
      + arn                    = (known after apply)
      + description            = "Allow all incoming HTTPS traffic to BAPE ALB and forward as HTTP to private subnets."
      + egress                 = (known after apply)
      + id                     = (known after apply)
      + ingress                = (known after apply)
      + name                   = "BAPE ALB SG"
      + name_prefix            = (known after apply)
      + owner_id               = (known after apply)
      + revoke_rules_on_delete = false
      + tags                   = {
          + "Name"  = "bape_alb_sg"
          + "Phase" = "phase-5-ecs"
        }
      + tags_all               = {
          + "Name"  = "bape_alb_sg"
          + "Phase" = "phase-5-ecs"
        }
      + vpc_id                 = (known after apply)
    }

  # aws_security_group.ecs_fargate_containers_sg will be created
  + resource "aws_security_group" "ecs_fargate_containers_sg" {
      + arn                    = (known after apply)
      + description            = "Allow incoming traffic from BAPE ALB SG and outgoing, private traffic to Gateway endpoints (ECR, S3, CloudWatch.)"
      + egress                 = (known after apply)
      + id                     = (known after apply)
      + ingress                = (known after apply)
      + name                   = "ECS Fargate Conatiners SG"
      + name_prefix            = (known after apply)
      + owner_id               = (known after apply)
      + revoke_rules_on_delete = false
      + tags                   = {
          + "Name"  = "ecs_fargate_containers_sg"
          + "Phase" = "phase-5-ecs"
        }
      + tags_all               = {
          + "Name"  = "ecs_fargate_containers_sg"
          + "Phase" = "phase-5-ecs"
        }
      + vpc_id                 = (known after apply)
    }

  # aws_security_group.vpc_endpoint_sg will be created
  + resource "aws_security_group" "vpc_endpoint_sg" {
      + arn                    = (known after apply)
      + description            = "SG for VPC endpoints"
      + egress                 = (known after apply)
      + id                     = (known after apply)
      + ingress                = (known after apply)
      + name                   = "vpc_endpoint_sg"
      + name_prefix            = (known after apply)
      + owner_id               = (known after apply)
      + revoke_rules_on_delete = false
      + tags                   = {
          + "Name"  = "vpc_endpoint_sg"
          + "Phase" = "phase-5-ecs"
        }
      + tags_all               = {
          + "Name"  = "vpc_endpoint_sg"
          + "Phase" = "phase-5-ecs"
        }
      + vpc_id                 = (known after apply)
    }

  # aws_subnet.prv-sn-A will be created
  + resource "aws_subnet" "prv-sn-A" {
      + arn                                            = (known after apply)
      + assign_ipv6_address_on_creation                = false
      + availability_zone                              = "eu-central-1a"
      + availability_zone_id                           = (known after apply)
      + cidr_block                                     = "10.0.3.0/24"
      + enable_dns64                                   = false
      + enable_resource_name_dns_a_record_on_launch    = false
      + enable_resource_name_dns_aaaa_record_on_launch = false
      + id                                             = (known after apply)
      + ipv6_cidr_block_association_id                 = (known after apply)
      + ipv6_native                                    = false
      + map_public_ip_on_launch                        = false
      + owner_id                                       = (known after apply)
      + private_dns_hostname_type_on_launch            = (known after apply)
      + tags                                           = {
          + "Name"  = "bape-vpc-prv-sn-A"
          + "Phase" = "phase-5-ecs"
        }
      + tags_all                                       = {
          + "Name"  = "bape-vpc-prv-sn-A"
          + "Phase" = "phase-5-ecs"
        }
      + vpc_id                                         = (known after apply)
    }

  # aws_subnet.prv-sn-B will be created
  + resource "aws_subnet" "prv-sn-B" {
      + arn                                            = (known after apply)
      + assign_ipv6_address_on_creation                = false
      + availability_zone                              = "eu-central-1b"
      + availability_zone_id                           = (known after apply)
      + cidr_block                                     = "10.0.4.0/24"
      + enable_dns64                                   = false
      + enable_resource_name_dns_a_record_on_launch    = false
      + enable_resource_name_dns_aaaa_record_on_launch = false
      + id                                             = (known after apply)
      + ipv6_cidr_block_association_id                 = (known after apply)
      + ipv6_native                                    = false
      + map_public_ip_on_launch                        = false
      + owner_id                                       = (known after apply)
      + private_dns_hostname_type_on_launch            = (known after apply)
      + tags                                           = {
          + "Name"  = "bape-vpc-prv-sn-B"
          + "Phase" = "phase-5-ecs"
        }
      + tags_all                                       = {
          + "Name"  = "bape-vpc-prv-sn-B"
          + "Phase" = "phase-5-ecs"
        }
      + vpc_id                                         = (known after apply)
    }

  # aws_subnet.pub-sn-A will be created
  + resource "aws_subnet" "pub-sn-A" {
      + arn                                            = (known after apply)
      + assign_ipv6_address_on_creation                = false
      + availability_zone                              = "eu-central-1a"
      + availability_zone_id                           = (known after apply)
      + cidr_block                                     = "10.0.1.0/24"
      + enable_dns64                                   = false
      + enable_resource_name_dns_a_record_on_launch    = false
      + enable_resource_name_dns_aaaa_record_on_launch = false
      + id                                             = (known after apply)
      + ipv6_cidr_block_association_id                 = (known after apply)
      + ipv6_native                                    = false
      + map_public_ip_on_launch                        = false
      + owner_id                                       = (known after apply)
      + private_dns_hostname_type_on_launch            = (known after apply)
      + tags                                           = {
          + "Name"  = "bape-vpc-pub-sn-A"
          + "Phase" = "phase-5-ecs"
        }
      + tags_all                                       = {
          + "Name"  = "bape-vpc-pub-sn-A"
          + "Phase" = "phase-5-ecs"
        }
      + vpc_id                                         = (known after apply)
    }

  # aws_subnet.pub-sn-B will be created
  + resource "aws_subnet" "pub-sn-B" {
      + arn                                            = (known after apply)
      + assign_ipv6_address_on_creation                = false
      + availability_zone                              = "eu-central-1b"
      + availability_zone_id                           = (known after apply)
      + cidr_block                                     = "10.0.2.0/24"
      + enable_dns64                                   = false
      + enable_resource_name_dns_a_record_on_launch    = false
      + enable_resource_name_dns_aaaa_record_on_launch = false
      + id                                             = (known after apply)
      + ipv6_cidr_block_association_id                 = (known after apply)
      + ipv6_native                                    = false
      + map_public_ip_on_launch                        = false
      + owner_id                                       = (known after apply)
      + private_dns_hostname_type_on_launch            = (known after apply)
      + tags                                           = {
          + "Name"  = "bape-vpc-pub-sn-B"
          + "Phase" = "phase-5-ecs"
        }
      + tags_all                                       = {
          + "Name"  = "bape-vpc-pub-sn-B"
          + "Phase" = "phase-5-ecs"
        }
      + vpc_id                                         = (known after apply)
    }

  # aws_vpc.bape-vpc will be created
  + resource "aws_vpc" "bape-vpc" {
      + arn                                  = (known after apply)
      + cidr_block                           = "10.0.0.0/16"
      + default_network_acl_id               = (known after apply)
      + default_route_table_id               = (known after apply)
      + default_security_group_id            = (known after apply)
      + dhcp_options_id                      = (known after apply)
      + enable_dns_hostnames                 = true
      + enable_dns_support                   = true
      + enable_network_address_usage_metrics = (known after apply)
      + id                                   = (known after apply)
      + instance_tenancy                     = "default"
      + ipv6_association_id                  = (known after apply)
      + ipv6_cidr_block                      = (known after apply)
      + ipv6_cidr_block_network_border_group = (known after apply)
      + main_route_table_id                  = (known after apply)
      + owner_id                             = (known after apply)
      + tags                                 = {
          + "Name"  = "bape-vpc"
          + "Phase" = "phase-5-ecs"
        }
      + tags_all                             = {
          + "Name"  = "bape-vpc"
          + "Phase" = "phase-5-ecs"
        }
    }

  # aws_vpc_endpoint.cloudwatch-logs-interface will be created
  + resource "aws_vpc_endpoint" "cloudwatch-logs-interface" {
      + arn                   = (known after apply)
      + cidr_blocks           = (known after apply)
      + dns_entry             = (known after apply)
      + id                    = (known after apply)
      + ip_address_type       = (known after apply)
      + network_interface_ids = (known after apply)
      + owner_id              = (known after apply)
      + policy                = (known after apply)
      + prefix_list_id        = (known after apply)
      + private_dns_enabled   = true
      + requester_managed     = (known after apply)
      + route_table_ids       = (known after apply)
      + security_group_ids    = (known after apply)
      + service_name          = "com.amazonaws.eu-central-1.logs"
      + service_region        = (known after apply)
      + state                 = (known after apply)
      + subnet_ids            = (known after apply)
      + tags                  = {
          + "Name"  = "bape-vpc-cw-logs-interface"
          + "Phase" = "phase-5-ecs"
        }
      + tags_all              = {
          + "Name"  = "bape-vpc-cw-logs-interface"
          + "Phase" = "phase-5-ecs"
        }
      + vpc_endpoint_type     = "Interface"
      + vpc_id                = (known after apply)

      + dns_options (known after apply)

      + subnet_configuration (known after apply)
    }

  # aws_vpc_endpoint.ecr-api-interface will be created
  + resource "aws_vpc_endpoint" "ecr-api-interface" {
      + arn                   = (known after apply)
      + cidr_blocks           = (known after apply)
      + dns_entry             = (known after apply)
      + id                    = (known after apply)
      + ip_address_type       = (known after apply)
      + network_interface_ids = (known after apply)
      + owner_id              = (known after apply)
      + policy                = (known after apply)
      + prefix_list_id        = (known after apply)
      + private_dns_enabled   = true
      + requester_managed     = (known after apply)
      + route_table_ids       = (known after apply)
      + security_group_ids    = (known after apply)
      + service_name          = "com.amazonaws.eu-central-1.ecr.api"
      + service_region        = (known after apply)
      + state                 = (known after apply)
      + subnet_ids            = (known after apply)
      + tags                  = {
          + "Name"  = "bape-vpc-ecr-api-interface"
          + "Phase" = "phase-5-ecs"
        }
      + tags_all              = {
          + "Name"  = "bape-vpc-ecr-api-interface"
          + "Phase" = "phase-5-ecs"
        }
      + vpc_endpoint_type     = "Interface"
      + vpc_id                = (known after apply)

      + dns_options (known after apply)

      + subnet_configuration (known after apply)
    }

  # aws_vpc_endpoint.ecr-dkr-interface will be created
  + resource "aws_vpc_endpoint" "ecr-dkr-interface" {
      + arn                   = (known after apply)
      + cidr_blocks           = (known after apply)
      + dns_entry             = (known after apply)
      + id                    = (known after apply)
      + ip_address_type       = (known after apply)
      + network_interface_ids = (known after apply)
      + owner_id              = (known after apply)
      + policy                = (known after apply)
      + prefix_list_id        = (known after apply)
      + private_dns_enabled   = true
      + requester_managed     = (known after apply)
      + route_table_ids       = (known after apply)
      + security_group_ids    = (known after apply)
      + service_name          = "com.amazonaws.eu-central-1.ecr.dkr"
      + service_region        = (known after apply)
      + state                 = (known after apply)
      + subnet_ids            = (known after apply)
      + tags                  = {
          + "Name"  = "bape-vpc-ecr-dkr-interface"
          + "Phase" = "phase-5-ecs"
        }
      + tags_all              = {
          + "Name"  = "bape-vpc-ecr-dkr-interface"
          + "Phase" = "phase-5-ecs"
        }
      + vpc_endpoint_type     = "Interface"
      + vpc_id                = (known after apply)

      + dns_options (known after apply)

      + subnet_configuration (known after apply)
    }

  # aws_vpc_endpoint.s3-gateway will be created
  + resource "aws_vpc_endpoint" "s3-gateway" {
      + arn                   = (known after apply)
      + cidr_blocks           = (known after apply)
      + dns_entry             = (known after apply)
      + id                    = (known after apply)
      + ip_address_type       = (known after apply)
      + network_interface_ids = (known after apply)
      + owner_id              = (known after apply)
      + policy                = (known after apply)
      + prefix_list_id        = (known after apply)
      + private_dns_enabled   = (known after apply)
      + requester_managed     = (known after apply)
      + route_table_ids       = (known after apply)
      + security_group_ids    = (known after apply)
      + service_name          = "com.amazonaws.eu-central-1.s3"
      + service_region        = (known after apply)
      + state                 = (known after apply)
      + subnet_ids            = (known after apply)
      + tags                  = {
          + "Name"  = "bape-vpc-s3-gw"
          + "Phase" = "phase-5-ecs"
        }
      + tags_all              = {
          + "Name"  = "bape-vpc-s3-gw"
          + "Phase" = "phase-5-ecs"
        }
      + vpc_endpoint_type     = "Gateway"
      + vpc_id                = (known after apply)

      + dns_options (known after apply)

      + subnet_configuration (known after apply)
    }

  # aws_vpc_security_group_egress_rule.bape_alb_sg_egress will be created
  + resource "aws_vpc_security_group_egress_rule" "bape_alb_sg_egress" {
      + arn                          = (known after apply)
      + from_port                    = 8080
      + id                           = (known after apply)
      + ip_protocol                  = "tcp"
      + referenced_security_group_id = (known after apply)
      + security_group_id            = (known after apply)
      + security_group_rule_id       = (known after apply)
      + tags_all                     = {}
      + to_port                      = 8080
    }

  # aws_vpc_security_group_egress_rule.ecs_fargate_egress will be created
  + resource "aws_vpc_security_group_egress_rule" "ecs_fargate_egress" {
      + arn                          = (known after apply)
      + from_port                    = 443
      + id                           = (known after apply)
      + ip_protocol                  = "tcp"
      + referenced_security_group_id = (known after apply)
      + security_group_id            = (known after apply)
      + security_group_rule_id       = (known after apply)
      + tags_all                     = {}
      + to_port                      = 443
    }

  # aws_vpc_security_group_egress_rule.ecs_fargate_s3_egress will be created
  + resource "aws_vpc_security_group_egress_rule" "ecs_fargate_s3_egress" {
      + arn                    = (known after apply)
      + from_port              = 443
      + id                     = (known after apply)
      + ip_protocol            = "tcp"
      + prefix_list_id         = "pl-6ea54007"
      + security_group_id      = (known after apply)
      + security_group_rule_id = (known after apply)
      + tags_all               = {}
      + to_port                = 443
    }

  # aws_vpc_security_group_ingress_rule.bape_alb_sg_ingress will be created
  + resource "aws_vpc_security_group_ingress_rule" "bape_alb_sg_ingress" {
      + arn                    = (known after apply)
      + cidr_ipv4              = "0.0.0.0/0"
      + from_port              = 80
      + id                     = (known after apply)
      + ip_protocol            = "tcp"
      + security_group_id      = (known after apply)
      + security_group_rule_id = (known after apply)
      + tags_all               = {}
      + to_port                = 80
    }

  # aws_vpc_security_group_ingress_rule.ecs_fargate_ingress will be created
  + resource "aws_vpc_security_group_ingress_rule" "ecs_fargate_ingress" {
      + arn                          = (known after apply)
      + from_port                    = 8080
      + id                           = (known after apply)
      + ip_protocol                  = "tcp"
      + referenced_security_group_id = (known after apply)
      + security_group_id            = (known after apply)
      + security_group_rule_id       = (known after apply)
      + tags_all                     = {}
      + to_port                      = 8080
    }

  # aws_vpc_security_group_ingress_rule.vpc_endpoint_ingress will be created
  + resource "aws_vpc_security_group_ingress_rule" "vpc_endpoint_ingress" {
      + arn                          = (known after apply)
      + from_port                    = 443
      + id                           = (known after apply)
      + ip_protocol                  = "tcp"
      + referenced_security_group_id = (known after apply)
      + security_group_id            = (known after apply)
      + security_group_rule_id       = (known after apply)
      + tags_all                     = {}
      + to_port                      = 443
    }

Plan: 37 to add, 0 to change, 0 to destroy.

Changes to Outputs:
  + bape-inference-tf-repository_url = "609662023678.dkr.ecr.eu-central-1.amazonaws.com/bape-inference-tf"

Do you want to perform these actions?
  Terraform will perform the actions described above.
  Only 'yes' will be accepted to approve.

  Enter a value: yes

aws_cloudwatch_log_group.log_group_ecs_bape_inference: Creating...
aws_vpc.bape-vpc: Creating...
aws_ecs_cluster.bape_cluster: Creating...
aws_iam_role.ecs_task_role: Creating...
aws_iam_role.ecs_task_execution_role: Creating...
aws_s3_bucket.bape_app_data_phase5: Creating...
aws_cloudwatch_log_group.log_group_ecs_bape_inference: Creation complete after 0s [id=log-group-ecs-bape-inference]
aws_s3_bucket.bape_app_data_phase5: Creation complete after 1s [id=bape-app-data-phase5-davidg]
aws_iam_role.ecs_task_role: Creation complete after 1s [id=bape-task-role]
aws_iam_role_policy.s3_access: Creating...
aws_iam_role.ecs_task_execution_role: Creation complete after 1s [id=bape-task-execution-role]
aws_iam_role_policy_attachment.execution_role_policy: Creating...
aws_ecs_task_definition.task_definition_bape: Creating...
aws_ecs_task_definition.task_definition_bape: Creation complete after 0s [id=task_definition_bape]
aws_iam_role_policy_attachment.execution_role_policy: Creation complete after 1s [id=bape-task-execution-role-20260415103841610500000001]
aws_iam_role_policy.s3_access: Creation complete after 1s [id=bape-task-role:bape-s3-access-policy]
aws_vpc.bape-vpc: Still creating... [00m10s elapsed]
aws_ecs_cluster.bape_cluster: Still creating... [00m10s elapsed]
aws_ecs_cluster.bape_cluster: Creation complete after 11s [id=arn:aws:ecs:eu-central-1:609662023678:cluster/bape_cluster]
aws_vpc.bape-vpc: Creation complete after 12s [id=vpc-0d53f59d14922a81e]
aws_subnet.prv-sn-A: Creating...
aws_security_group.ecs_fargate_containers_sg: Creating...
aws_subnet.pub-sn-B: Creating...
aws_subnet.pub-sn-A: Creating...
aws_route_table.private-traffic: Creating...
aws_security_group.vpc_endpoint_sg: Creating...
aws_subnet.prv-sn-B: Creating...
aws_lb_target_group.bape_alb_tg: Creating...
aws_security_group.bape_alb_sg: Creating...
aws_internet_gateway.igw: Creating...
aws_route_table.private-traffic: Creation complete after 0s [id=rtb-0ce14c2ecfce54c39]
aws_vpc_endpoint.s3-gateway: Creating...
aws_subnet.pub-sn-A: Creation complete after 0s [id=subnet-02c5facea838f4295]
aws_internet_gateway.igw: Creation complete after 0s [id=igw-01451254df617627f]
aws_subnet.prv-sn-A: Creation complete after 0s [id=subnet-0054e9b2822bd0898]
aws_route_table_association.prv-sn-a-assoc: Creating...
aws_route_table.all-traffic-to-igw: Creating...
aws_lb_target_group.bape_alb_tg: Creation complete after 1s [id=arn:aws:elasticloadbalancing:eu-central-1:609662023678:targetgroup/bape-alb-tg/e5d0d410d442450d]
aws_route_table_association.prv-sn-a-assoc: Creation complete after 1s [id=rtbassoc-092884035032539b6]
aws_route_table.all-traffic-to-igw: Creation complete after 1s [id=rtb-064ee4e2f9ddee2b3]
aws_route_table_association.pub-sn-a-assoc: Creating...
aws_route_table_association.pub-sn-a-assoc: Creation complete after 1s [id=rtbassoc-0879a9e5d1a5649b5]
aws_security_group.vpc_endpoint_sg: Creation complete after 2s [id=sg-07e26e8a540631d16]
aws_security_group.ecs_fargate_containers_sg: Creation complete after 2s [id=sg-062df48ceac2147f8]
aws_security_group.bape_alb_sg: Creation complete after 2s [id=sg-0a411e16355125498]
aws_vpc_security_group_egress_rule.ecs_fargate_egress: Creating...
aws_vpc_security_group_egress_rule.bape_alb_sg_egress: Creating...
aws_vpc_security_group_ingress_rule.bape_alb_sg_ingress: Creating...
aws_vpc_security_group_ingress_rule.ecs_fargate_ingress: Creating...
aws_vpc_security_group_ingress_rule.vpc_endpoint_ingress: Creating...
aws_vpc_security_group_egress_rule.ecs_fargate_s3_egress: Creating...
aws_vpc_security_group_ingress_rule.bape_alb_sg_ingress: Creation complete after 0s [id=sgr-0f12f185b23f653b4]
aws_vpc_security_group_ingress_rule.vpc_endpoint_ingress: Creation complete after 0s [id=sgr-0b6541f31ce75ac17]
aws_vpc_security_group_ingress_rule.ecs_fargate_ingress: Creation complete after 0s [id=sgr-0bb3baa48fb946f68]
aws_vpc_security_group_egress_rule.ecs_fargate_s3_egress: Creation complete after 0s [id=sgr-0cd774d7e40754ff1]
aws_vpc_security_group_egress_rule.bape_alb_sg_egress: Creation complete after 0s [id=sgr-09f2f37a227668679]
aws_vpc_security_group_egress_rule.ecs_fargate_egress: Creation complete after 0s [id=sgr-05dd91d85c5edb35b]
aws_subnet.prv-sn-B: Creation complete after 3s [id=subnet-0b35bcb7e7a2eb90a]
aws_route_table_association.prv-sn-b-assoc: Creating...
aws_vpc_endpoint.cloudwatch-logs-interface: Creating...
aws_vpc_endpoint.ecr-api-interface: Creating...
aws_vpc_endpoint.ecr-dkr-interface: Creating...
aws_ecs_service.bape_service: Creating...
aws_route_table_association.prv-sn-b-assoc: Creation complete after 1s [id=rtbassoc-0fb96e9ea33f221a6]
aws_subnet.pub-sn-B: Creation complete after 4s [id=subnet-014cedd51b87cbd00]
aws_route_table_association.pub-sn-b-assoc: Creating...
aws_lb.bape_alb: Creating...
aws_route_table_association.pub-sn-b-assoc: Creation complete after 0s [id=rtbassoc-004f08e3d1f555966]
aws_vpc_endpoint.s3-gateway: Creation complete after 6s [id=vpce-0aa6920b06dc84444]
aws_vpc_endpoint.ecr-dkr-interface: Still creating... [00m10s elapsed]
aws_vpc_endpoint.cloudwatch-logs-interface: Still creating... [00m10s elapsed]
aws_vpc_endpoint.ecr-api-interface: Still creating... [00m10s elapsed]
aws_ecs_service.bape_service: Still creating... [00m10s elapsed]
aws_lb.bape_alb: Still creating... [00m10s elapsed]
aws_vpc_endpoint.ecr-api-interface: Still creating... [00m20s elapsed]
aws_vpc_endpoint.cloudwatch-logs-interface: Still creating... [00m20s elapsed]
aws_vpc_endpoint.ecr-dkr-interface: Still creating... [00m20s elapsed]
aws_ecs_service.bape_service: Still creating... [00m20s elapsed]
aws_lb.bape_alb: Still creating... [00m20s elapsed]
aws_vpc_endpoint.cloudwatch-logs-interface: Still creating... [00m30s elapsed]
aws_vpc_endpoint.ecr-dkr-interface: Still creating... [00m30s elapsed]
aws_vpc_endpoint.ecr-api-interface: Still creating... [00m30s elapsed]
aws_ecs_service.bape_service: Still creating... [00m30s elapsed]
aws_lb.bape_alb: Still creating... [00m30s elapsed]
aws_vpc_endpoint.ecr-api-interface: Still creating... [00m40s elapsed]
aws_vpc_endpoint.ecr-dkr-interface: Still creating... [00m40s elapsed]
aws_vpc_endpoint.cloudwatch-logs-interface: Still creating... [00m40s elapsed]
aws_ecs_service.bape_service: Still creating... [00m40s elapsed]
aws_lb.bape_alb: Still creating... [00m40s elapsed]
aws_vpc_endpoint.cloudwatch-logs-interface: Creation complete after 43s [id=vpce-0281f622491c2bf54]
aws_vpc_endpoint.ecr-dkr-interface: Creation complete after 43s [id=vpce-065a16d334edcf50e]
aws_vpc_endpoint.ecr-api-interface: Creation complete after 43s [id=vpce-0dbdf875b44ed7483]
aws_ecs_service.bape_service: Still creating... [00m50s elapsed]
aws_lb.bape_alb: Still creating... [00m50s elapsed]
aws_ecs_service.bape_service: Still creating... [01m00s elapsed]
aws_lb.bape_alb: Still creating... [01m00s elapsed]
aws_ecs_service.bape_service: Still creating... [01m10s elapsed]
aws_lb.bape_alb: Still creating... [01m10s elapsed]
aws_ecs_service.bape_service: Still creating... [01m20s elapsed]
aws_lb.bape_alb: Still creating... [01m20s elapsed]
aws_ecs_service.bape_service: Still creating... [01m30s elapsed]
aws_lb.bape_alb: Still creating... [01m30s elapsed]
aws_ecs_service.bape_service: Still creating... [01m40s elapsed]
aws_lb.bape_alb: Still creating... [01m40s elapsed]
aws_ecs_service.bape_service: Still creating... [01m50s elapsed]
aws_lb.bape_alb: Still creating... [01m50s elapsed]
aws_ecs_service.bape_service: Still creating... [02m00s elapsed]
aws_lb.bape_alb: Still creating... [02m00s elapsed]
aws_ecs_service.bape_service: Still creating... [02m10s elapsed]
aws_lb.bape_alb: Still creating... [02m10s elapsed]
aws_lb.bape_alb: Creation complete after 2m11s [id=arn:aws:elasticloadbalancing:eu-central-1:609662023678:loadbalancer/app/bape-alb/37fbc7a0f9f3f713]
aws_lb_listener.bape_alb_listener: Creating...
aws_lb_listener.bape_alb_listener: Creation complete after 0s [id=arn:aws:elasticloadbalancing:eu-central-1:609662023678:listener/app/bape-alb/37fbc7a0f9f3f713/e078b46eb0b2fb7a]
aws_ecs_service.bape_service: Creation complete after 2m17s [id=arn:aws:ecs:eu-central-1:609662023678:service/bape_cluster/bape_ecs_service]

Apply complete! Resources: 37 added, 0 changed, 0 destroyed.

Outputs:

bape-inference-tf-repository_url = "609662023678.dkr.ecr.eu-central-1.amazonaws.com/bape-inference-tf"
```