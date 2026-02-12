terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "4.11.0"
    }
  }
}

provider "aws" {
  # Configuration options
  region = "us-east-1"
  default_tags {
    tags = {
      Environment  = terraform.workspace
      ManagedBy    = "Terraform"
      InfraVersion = "1.0.0"
      Project      = "DegressLMS"
      Owner        = "dipesh.garg"
    }
  }
}
