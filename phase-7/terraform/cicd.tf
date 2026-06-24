# ID PROVIDER: GitHub
resource "aws_iam_openid_connect_provider" "github_oidc" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["1c58a3a8518e8759bf075b76b750d4f2df264fcd", "6938fd4d98bab03faadb97b34396831e3780aea1"]
}

# ROLE: GitHub's Badge
resource "aws_iam_role" "github_actions_role" {
  name = "github_actions_bape_cd"

  # TRUST POLICY: The Badges details about the provider
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        Action : "sts:AssumeRoleWithWebIdentity",
        Effect : "Allow",
        Principal : {
          Federated : aws_iam_openid_connect_provider.github_oidc.arn
        },

        Condition : {
          StringEquals : {
            # restrict AWS access to pushes only on container-orchestration branch
            "token.actions.githubusercontent.com:sub" : "repo:dielaenge/onnx-deployment:ref:refs/heads/feat/phase7",
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })
}

# PERMISSIONS POLICY: The permissions attached to the GitHub Actions' badge

resource "aws_iam_role_policy" "github_actions_permissions" {
  name = "github-actions-bape-permissions-policy"
  role = aws_iam_role.github_actions_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Permission to download the ONNX and ONNX.DATA during CI/CD build
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::bape-app-data-phase7-davidg",  # Allows listing the bucket / addressed explicitly to avoid dependency applies when running target applies
          "arn:aws:s3:::bape-app-data-phase7-davidg/*" # Allows downloading the files inside addressed explicitly to avoid dependency applies when running target applies
        ]
      },
      {
        # Permission to login to ECR
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
        # Permission to push to bape-phase7 ECR repository
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:GetRepositoryPolicy",
          "ecr:DescribeRepositories",
          "ecr:ListImages",
          "ecr:DescribeImages",
          "ecr:BatchGetImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage"
        ]
        Resource = "arn:aws:ecr:eu-central-1:${data.aws_caller_identity.current.account_id}:repository/bape-ecr-phase7" #addressed explicitly to avoid dependency applies when running target applies
      },
      {
        # Permission to force a new deployment in ECS
        Effect = "Allow"
        Action = [
          "ecs:UpdateService",
          "ecs:DescribeServices"
        ]
        Resource = "arn:aws:ecs:eu-central-1:${data.aws_caller_identity.current.account_id}:service/bape_cluster/bape_ecs_service" #addressed explicitly to avoid dependency applies when running target applies
      }
    ]
  })
}