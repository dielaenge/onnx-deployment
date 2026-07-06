# ALL PROVIDER BLOCKS AND CONFIGURATION

data "aws_region" "current" {}

provider "aws" {

  region = var.aws_region

  default_tags {
    tags = {
      Phase          = "phase7"
      ManagedBy      = "Terraform"
      AWSEnvironment = "dev"
    }
  }

}