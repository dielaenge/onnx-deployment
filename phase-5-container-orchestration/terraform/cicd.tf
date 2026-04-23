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
            "token.actions.githubusercontent.com:sub" : "repo:dielaenge/onnx-deployment:ref:refs/heads/feat/container-orchestration",
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })
}

# PERMISSIONS POLICY: The permissions attached to the GitHub Actions' badge

resource "aws_iam_role_policy" "github_actions_permissions" {
  name = "github-actions-bape-premissions-policy"
  role = aws_iam_role.github_actions_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Permission to login to ECR
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
        # Permission to push to bape-inference-tf ECR repository
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
        Resource = aws_ecr_repository.bape-inference-tf.arn
      },
      {
        # Permission to force a new deployment in ECS
        Effect = "Allow"
        Action = [
          "ecs:UpdateService",
          "ecs:DescribeServices"
        ]
        Resource = aws_ecs_service.bape_service.id
      }
    ]
  })
}