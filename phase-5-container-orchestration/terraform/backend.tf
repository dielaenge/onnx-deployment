# Backend Config

terraform {
  backend "s3" {
    bucket       = "bape-tf-state-davidg-2026"
    key          = "bape/production/terraform.tfstate"
    region       = "eu-central-1"
    use_lockfile = true
    encrypt      = true
    profile      = "dev"
  }
}