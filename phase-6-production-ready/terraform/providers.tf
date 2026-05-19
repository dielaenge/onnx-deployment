# ALL PROVIDER BLOCKS AND CONFIGURATION

provider "aws" {

    region = "eu-central-1"

    default_tags {
      tags = {
        Phase = "phase6"
        ManagedBy = "Terraform"
        AWSEnvironment = "dev"
      }
    }

}