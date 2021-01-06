terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.22"
    }

    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }

    external = {
      source  = "hashicorp/external"
      version = "~> 2.0"
    }
  }

  required_version = "~> 0.14.2"
}
