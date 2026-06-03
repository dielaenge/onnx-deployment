# ALL PROVIDER BLOCKS AND CONFIGURATION

provider "aws" {

    region = "eu-central-1"

    default_tags {
      tags = {
        Phase = "phase7"
        ManagedBy = "Terraform"
        AWSEnvironment = "dev"
      }
    }

}